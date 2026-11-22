use crate::error::ConfigError;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use url::Url;

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ServiceConfig {
    pub webservice: WebServerConfig,
    #[serde(default)]
    pub auth: Option<AuthConfig>,
    #[serde(default)]
    pub persistence: Option<PersistenceConfig>,
    #[serde(default)]
    pub hams: Option<HamsConfig>,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
pub struct WebServerConfig {
    pub url: Url,
    pub prefix: String,
}

impl WebServerConfig {
    /// Extracts the TCP port from `webservice.url` using `Url::port_or_known_default()`,
    /// verifying that the scheme is `http` or `https` and a host is present.
    pub fn port(&self) -> Result<u16, ConfigError> {
        if !matches!(self.url.scheme(), "http" | "https") {
            return Err(ConfigError::InvalidWebServerUrl(self.url.to_string()));
        }
        if self.url.host_str().is_none_or(|h| h.is_empty()) {
            return Err(ConfigError::InvalidWebServerUrl(self.url.to_string()));
        }
        let port = self
            .url
            .port_or_known_default()
            .ok_or_else(|| ConfigError::InvalidWebServerPort(self.url.to_string()))?;
        if port == 0 {
            return Err(ConfigError::InvalidWebServerPort(self.url.to_string()));
        }
        Ok(port)
    }

    pub fn validate(&self) -> Result<(), ConfigError> {
        self.port()?;
        if !self.prefix.is_empty() && self.prefix.trim().is_empty() {
            return Err(ConfigError::InvalidWebServerPrefix(
                "prefix cannot be whitespace-only".to_string(),
            ));
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct AuthConfig {
    pub jwt_public_key: String,
    pub jwt_issuer: String,
    pub jwt_audience: String,
}

impl AuthConfig {
    pub fn decoding_key(&self) -> Result<jsonwebtoken::DecodingKey, jsonwebtoken::errors::Error> {
        let pem = self.jwt_public_key.replace("\\n", "\n");
        jsonwebtoken::DecodingKey::from_rsa_pem(pem.as_bytes())
    }

    pub fn validate(&self) -> Result<(), ConfigError> {
        if self.jwt_public_key.trim().is_empty() {
            return Err(ConfigError::InvalidAuthConfig(
                "jwt_public_key cannot be empty".to_string(),
            ));
        }
        self.decoding_key().map_err(|e| {
            ConfigError::InvalidAuthConfig(format!("invalid jwt_public_key RSA PEM: {e}"))
        })?;
        if self.jwt_issuer.trim().is_empty() {
            return Err(ConfigError::InvalidAuthConfig(
                "jwt_issuer cannot be empty".to_string(),
            ));
        }
        if self.jwt_audience.trim().is_empty() {
            return Err(ConfigError::InvalidAuthConfig(
                "jwt_audience cannot be empty".to_string(),
            ));
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct PersistenceConfig {
    pub db: Option<DbConfig>,
}

impl PersistenceConfig {
    pub fn validate(&self) -> Result<(), ConfigError> {
        if let Some(ref db) = self.db {
            db.validate()?;
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct DbConfig {
    pub pool_size: Option<u32>,
    pub automigrate: Option<bool>,
    pub acquire_timeout: Option<u64>,
    pub connection: Option<DbConnectionConfig>,
}

impl DbConfig {
    pub fn validate(&self) -> Result<(), ConfigError> {
        if let Some(0) = self.pool_size {
            return Err(ConfigError::InvalidDbConfig(
                "pool_size must be greater than 0".to_string(),
            ));
        }
        if let Some(0) = self.acquire_timeout {
            return Err(ConfigError::InvalidDbConfig(
                "acquire_timeout must be greater than 0".to_string(),
            ));
        }
        if let Some(ref conn) = self.connection {
            if let Some(ref url) = conn.url {
                if url.trim().is_empty() {
                    return Err(ConfigError::InvalidDbConfig(
                        "connection.url cannot be empty".to_string(),
                    ));
                }
            }
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct DbConnectionConfig {
    pub url: Option<String>,
    pub username: Option<String>,
    pub password: Option<String>,
}

impl DbConnectionConfig {
    pub fn dsn(&self) -> Option<String> {
        let base_url = self.url.as_deref()?;
        let clean_base = base_url
            .strip_prefix("postgresql://")
            .or_else(|| base_url.strip_prefix("postgres://"))
            .unwrap_or(base_url);

        match (&self.username, &self.password) {
            (Some(user), Some(pass)) => {
                Some(format!("postgresql://{}:{}@{}", user, pass, clean_base))
            }
            (Some(user), None) => Some(format!("postgresql://{}@{}", user, clean_base)),
            (None, None) => Some(format!("postgresql://{}", clean_base)),
            (None, Some(pass)) => Some(format!("postgresql://:{}@{}", pass, clean_base)),
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct HamsConfig {
    pub url: Option<String>,
    pub port: Option<u16>,
    pub prefix: Option<String>,
}

impl HamsConfig {
    pub fn validate(&self) -> Result<(), ConfigError> {
        if let Some(0) = self.port {
            return Err(ConfigError::InvalidHamsConfig(
                "hams.port must be greater than 0".to_string(),
            ));
        }
        Ok(())
    }
}

impl ServiceConfig {
    pub fn from_yaml_and_secrets(
        yaml_path: &Path,
        secrets_path: Option<&Path>,
    ) -> Result<Self, ConfigError> {
        let content = fs::read_to_string(yaml_path).map_err(|source| ConfigError::ReadFile {
            path: yaml_path.to_path_buf(),
            source,
        })?;
        let mut config: ServiceConfig =
            serde_yaml::from_str(&content).map_err(|source| ConfigError::ParseYaml {
                path: yaml_path.to_path_buf(),
                source,
            })?;

        // If secrets dir is specified, require it to exist and be a directory
        if let Some(sec_dir) = secrets_path {
            if !sec_dir.exists() || !sec_dir.is_dir() {
                return Err(ConfigError::InvalidSecretsDir {
                    path: sec_dir.to_path_buf(),
                });
            }
            config.load_secrets(sec_dir)?;
        }

        config.validate()?;
        Ok(config)
    }

    pub fn validate(&self) -> Result<(), ConfigError> {
        self.webservice.validate()?;
        if let Some(ref auth) = self.auth {
            auth.validate()?;
        }
        if let Some(ref persistence) = self.persistence {
            persistence.validate()?;
        }
        if let Some(ref hams) = self.hams {
            hams.validate()?;
        }
        Ok(())
    }

    fn load_secrets(&mut self, secrets_dir: &Path) -> Result<(), ConfigError> {
        // Look for persistence/db/connection/username and password
        let user_file = secrets_dir.join("persistence/db/connection/username");
        if user_file.exists() {
            let u = fs::read_to_string(&user_file).map_err(|source| ConfigError::ReadSecret {
                path: user_file,
                source,
            })?;
            if let Some(ref mut p) = self.persistence {
                if let Some(ref mut db) = p.db {
                    if let Some(ref mut conn) = db.connection {
                        conn.username = Some(u.trim().to_string());
                    }
                }
            }
        }

        let pass_file = secrets_dir.join("persistence/db/connection/password");
        if pass_file.exists() {
            let p_str =
                fs::read_to_string(&pass_file).map_err(|source| ConfigError::ReadSecret {
                    path: pass_file,
                    source,
                })?;
            if let Some(ref mut p) = self.persistence {
                if let Some(ref mut db) = p.db {
                    if let Some(ref mut conn) = db.connection {
                        conn.password = Some(p_str.trim().to_string());
                    }
                }
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;
    use uuid::Uuid;

    fn temp_config_path(name: &str) -> PathBuf {
        std::env::temp_dir().join(format!("agentrs_be_test_{}_{}.yaml", name, Uuid::new_v4()))
    }

    fn base_service_config() -> ServiceConfig {
        ServiceConfig {
            webservice: WebServerConfig {
                url: Url::parse("http://0.0.0.0:8080/agent-be").unwrap(),
                prefix: "/api/angry-agent/v1".to_string(),
            },
            auth: None,
            persistence: None,
            hams: None,
        }
    }

    #[test]
    fn webserver_port_parses_standard_and_path_suffixed_urls() {
        let cfg = WebServerConfig {
            url: Url::parse("http://0.0.0.0:8080").unwrap(),
            prefix: "/api".to_string(),
        };
        assert_eq!(cfg.port().unwrap(), 8080);

        let cfg_with_path = WebServerConfig {
            url: Url::parse("http://0.0.0.0:8080/agent-be").unwrap(),
            prefix: "/api/angry-agent/v1".to_string(),
        };
        assert_eq!(cfg_with_path.port().unwrap(), 8080);

        let cfg_https_with_query = WebServerConfig {
            url: Url::parse("https://api.example.com:8443/agent-be?debug=1#frag").unwrap(),
            prefix: "/api".to_string(),
        };
        assert_eq!(cfg_https_with_query.port().unwrap(), 8443);

        let cfg_ipv6 = WebServerConfig {
            url: Url::parse("http://[::]:9090/agent-be").unwrap(),
            prefix: "/api".to_string(),
        };
        assert_eq!(cfg_ipv6.port().unwrap(), 9090);

        let cfg_default_http = WebServerConfig {
            url: Url::parse("http://example.com/agent-be").unwrap(),
            prefix: "/api".to_string(),
        };
        assert_eq!(cfg_default_http.port().unwrap(), 80);

        let cfg_default_https = WebServerConfig {
            url: Url::parse("https://example.com/agent-be").unwrap(),
            prefix: "/api".to_string(),
        };
        assert_eq!(cfg_default_https.port().unwrap(), 443);
    }

    #[test]
    fn webserver_port_rejects_invalid_urls_and_ports() {
        let ftp_cfg = WebServerConfig {
            url: Url::parse("ftp://0.0.0.0:8080").unwrap(),
            prefix: "/api".to_string(),
        };
        assert!(matches!(
            ftp_cfg.port(),
            Err(ConfigError::InvalidWebServerUrl(_))
        ));

        let zero_port_cfg = WebServerConfig {
            url: Url::parse("http://0.0.0.0:0/agent-be").unwrap(),
            prefix: "/api".to_string(),
        };
        assert!(matches!(
            zero_port_cfg.port(),
            Err(ConfigError::InvalidWebServerPort(_))
        ));

        for unparseable_yaml in [
            "url: \"\"\nprefix: \"/api\"",
            "url: \"0.0.0.0:8080\"\nprefix: \"/api\"",
            "url: \"http://:8080/agent-be\"\nprefix: \"/api\"",
            "url: \"http://0.0.0.0:99999/agent-be\"\nprefix: \"/api\"",
            "url: \"http://0.0.0.0:notaport/agent-be\"\nprefix: \"/api\"",
            "prefix: \"/api\"",
            "url: \"http://0.0.0.0:8080\"",
        ] {
            assert!(
                serde_yaml::from_str::<WebServerConfig>(unparseable_yaml).is_err(),
                "expected YAML deserialization failure for {unparseable_yaml}"
            );
        }
    }

    #[test]
    fn validate_accepts_base_config() {
        let cfg = base_service_config();
        assert!(cfg.validate().is_ok());
    }

    const TEST_RSA_PUBLIC_KEY_PEM: &str = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqcAgTagDgfhm3VCxV4FA\nWl3Yos4/f9xyFNkJwkudV4b52KcLSHomBEVFfIb65CnSJUHIs8E0vLda3wmZTNdc\nld9K7a4stkfItDGd1JJKqAZNiYlWkgwwMj+TeQUt4mbiVUvt2KZY78r4RlrKE1w7\nGuzs711R/HZz7mz4FFiNAR4GRynZHH6BLbIJA8EJ+JvtRJZ59tybWpuZt5bUUbxv\n9V1fQsF2HR6jCvt/OnctqarMfHm3B/0Ko0EtXCNhzJIqlByvw1n8u0pDEMoLUkOv\neXvigynPOk29FEEYji+UOEvZZHMpMHqgZukUr9dDKYysj18mr06zgpy9HWxEXU1J\n4wIDAQAB\n-----END PUBLIC KEY-----";

    #[test]
    fn validate_accepts_valid_auth_config_with_rsa_pem() {
        let cfg = ServiceConfig {
            auth: Some(AuthConfig {
                jwt_public_key: TEST_RSA_PUBLIC_KEY_PEM.to_string(),
                jwt_issuer: "https://issuer".to_string(),
                jwt_audience: "aud".to_string(),
            }),
            ..base_service_config()
        };
        assert!(cfg.validate().is_ok());

        let cfg_escaped_newlines = ServiceConfig {
            auth: Some(AuthConfig {
                jwt_public_key: TEST_RSA_PUBLIC_KEY_PEM.replace('\n', "\\n"),
                jwt_issuer: "https://issuer".to_string(),
                jwt_audience: "aud".to_string(),
            }),
            ..base_service_config()
        };
        assert!(cfg_escaped_newlines.validate().is_ok());
    }

    #[test]
    fn validate_rejects_invalid_auth_config() {
        let cfg = ServiceConfig {
            auth: Some(AuthConfig {
                jwt_public_key: "   ".to_string(),
                jwt_issuer: "https://issuer".to_string(),
                jwt_audience: "aud".to_string(),
            }),
            ..base_service_config()
        };
        assert!(matches!(
            cfg.validate(),
            Err(ConfigError::InvalidAuthConfig(_))
        ));

        let cfg_malformed_pem = ServiceConfig {
            auth: Some(AuthConfig {
                jwt_public_key: "not-a-valid-rsa-pem".to_string(),
                jwt_issuer: "https://issuer".to_string(),
                jwt_audience: "aud".to_string(),
            }),
            ..base_service_config()
        };
        assert!(matches!(
            cfg_malformed_pem.validate(),
            Err(ConfigError::InvalidAuthConfig(_))
        ));

        let cfg_empty_issuer = ServiceConfig {
            auth: Some(AuthConfig {
                jwt_public_key: TEST_RSA_PUBLIC_KEY_PEM.to_string(),
                jwt_issuer: "".to_string(),
                jwt_audience: "aud".to_string(),
            }),
            ..base_service_config()
        };
        assert!(matches!(
            cfg_empty_issuer.validate(),
            Err(ConfigError::InvalidAuthConfig(_))
        ));

        let cfg_empty_aud = ServiceConfig {
            auth: Some(AuthConfig {
                jwt_public_key: TEST_RSA_PUBLIC_KEY_PEM.to_string(),
                jwt_issuer: "https://issuer".to_string(),
                jwt_audience: " ".to_string(),
            }),
            ..base_service_config()
        };
        assert!(matches!(
            cfg_empty_aud.validate(),
            Err(ConfigError::InvalidAuthConfig(_))
        ));
    }

    #[test]
    fn validate_rejects_invalid_db_and_hams_config() {
        let cfg_zero_pool = ServiceConfig {
            persistence: Some(PersistenceConfig {
                db: Some(DbConfig {
                    pool_size: Some(0),
                    ..Default::default()
                }),
            }),
            ..base_service_config()
        };
        assert!(matches!(
            cfg_zero_pool.validate(),
            Err(ConfigError::InvalidDbConfig(_))
        ));

        let cfg_zero_timeout = ServiceConfig {
            persistence: Some(PersistenceConfig {
                db: Some(DbConfig {
                    acquire_timeout: Some(0),
                    ..Default::default()
                }),
            }),
            ..base_service_config()
        };
        assert!(matches!(
            cfg_zero_timeout.validate(),
            Err(ConfigError::InvalidDbConfig(_))
        ));

        let cfg_empty_db_url = ServiceConfig {
            persistence: Some(PersistenceConfig {
                db: Some(DbConfig {
                    connection: Some(DbConnectionConfig {
                        url: Some("  ".to_string()),
                        ..Default::default()
                    }),
                    ..Default::default()
                }),
            }),
            ..base_service_config()
        };
        assert!(matches!(
            cfg_empty_db_url.validate(),
            Err(ConfigError::InvalidDbConfig(_))
        ));

        let cfg_zero_hams_port = ServiceConfig {
            hams: Some(HamsConfig {
                port: Some(0),
                ..Default::default()
            }),
            ..base_service_config()
        };
        assert!(matches!(
            cfg_zero_hams_port.validate(),
            Err(ConfigError::InvalidHamsConfig(_))
        ));
    }

    #[test]
    fn from_yaml_and_secrets_fails_fast_on_missing_or_invalid_yaml() {
        let missing = temp_config_path("missing");
        let err = ServiceConfig::from_yaml_and_secrets(&missing, None).unwrap_err();
        assert!(matches!(err, ConfigError::ReadFile { .. }));

        let invalid_yaml = temp_config_path("invalid");
        fs::write(&invalid_yaml, "webservice: [not: valid: yaml").unwrap();
        let err = ServiceConfig::from_yaml_and_secrets(&invalid_yaml, None).unwrap_err();
        let _ = fs::remove_file(&invalid_yaml);
        assert!(matches!(err, ConfigError::ParseYaml { .. }));
    }

    #[test]
    fn from_yaml_and_secrets_fails_fast_on_missing_or_non_directory_secrets_path() {
        let valid_yaml = temp_config_path("valid_for_secrets");
        fs::write(
            &valid_yaml,
            r#"
webservice:
  url: http://0.0.0.0:8080/agent-be
  prefix: "/api/angry-agent/v1"
"#,
        )
        .unwrap();

        let missing_dir =
            std::env::temp_dir().join(format!("nonexistent_secrets_{}", Uuid::new_v4()));
        let err =
            ServiceConfig::from_yaml_and_secrets(&valid_yaml, Some(&missing_dir)).unwrap_err();
        assert!(matches!(err, ConfigError::InvalidSecretsDir { .. }));

        // Passing a regular file instead of a directory must also fail fast
        let err_file =
            ServiceConfig::from_yaml_and_secrets(&valid_yaml, Some(&valid_yaml)).unwrap_err();
        let _ = fs::remove_file(&valid_yaml);
        assert!(matches!(err_file, ConfigError::InvalidSecretsDir { .. }));
    }

    #[test]
    fn from_yaml_and_secrets_loads_valid_yaml_and_validates() {
        let valid_yaml = temp_config_path("valid");
        fs::write(
            &valid_yaml,
            r#"
webservice:
  url: http://0.0.0.0:8080/agent-be
  prefix: "/api/angry-agent/v1"
persistence:
  db:
    pool_size: 10
    acquire_timeout: 5
    connection:
      url: postgresql://localhost:5432/agentdb
"#,
        )
        .unwrap();

        let cfg = ServiceConfig::from_yaml_and_secrets(&valid_yaml, None)
            .expect("valid YAML should load and validate");
        let _ = fs::remove_file(&valid_yaml);
        assert_eq!(cfg.webservice.port().unwrap(), 8080);
        assert_eq!(cfg.webservice.prefix, "/api/angry-agent/v1");
    }
}
