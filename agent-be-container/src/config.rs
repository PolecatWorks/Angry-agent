use crate::error::ConfigError;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct ServiceConfig {
    #[serde(default)]
    pub webservice: WebServerConfig,
    #[serde(default)]
    pub auth: Option<AuthConfig>,
    #[serde(default)]
    pub persistence: Option<PersistenceConfig>,
    #[serde(default)]
    pub hams: Option<HamsConfig>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct WebServerConfig {
    #[serde(default = "default_url")]
    pub url: String,
    #[serde(default = "default_prefix")]
    pub prefix: String,
}

impl Default for WebServerConfig {
    fn default() -> Self {
        Self {
            url: default_url(),
            prefix: default_prefix(),
        }
    }
}

impl WebServerConfig {
    /// Extracts the TCP port from `webservice.url`, properly handling path,
    /// query, and fragment suffixes (e.g. `http://0.0.0.0:8080/agent-be`).
    pub fn port(&self) -> Result<u16, ConfigError> {
        let trimmed = self.url.trim();
        let after_scheme = trimmed
            .strip_prefix("http://")
            .or_else(|| trimmed.strip_prefix("https://"))
            .ok_or_else(|| ConfigError::InvalidWebServerUrl(self.url.clone()))?;

        let authority = after_scheme.split(['/', '?', '#']).next().unwrap_or("");
        if authority.is_empty() {
            return Err(ConfigError::InvalidWebServerUrl(self.url.clone()));
        }

        let host_port = authority
            .rsplit_once('@')
            .map(|(_, hp)| hp)
            .unwrap_or(authority);

        let port_str = if let Some(rest) = host_port.strip_prefix('[') {
            let (host, after_bracket) = rest
                .split_once(']')
                .ok_or_else(|| ConfigError::InvalidWebServerUrl(self.url.clone()))?;
            if host.is_empty() {
                return Err(ConfigError::InvalidWebServerUrl(self.url.clone()));
            }
            if after_bracket.is_empty() {
                None
            } else {
                let p = after_bracket
                    .strip_prefix(':')
                    .ok_or_else(|| ConfigError::InvalidWebServerUrl(self.url.clone()))?;
                Some(p)
            }
        } else if let Some((host, p)) = host_port.rsplit_once(':') {
            if host.is_empty() {
                return Err(ConfigError::InvalidWebServerUrl(self.url.clone()));
            }
            Some(p)
        } else {
            if host_port.is_empty() {
                return Err(ConfigError::InvalidWebServerUrl(self.url.clone()));
            }
            None
        };

        match port_str {
            Some(p) => {
                let port: u16 = p
                    .parse()
                    .map_err(|_| ConfigError::InvalidWebServerPort(self.url.clone()))?;
                if port == 0 {
                    return Err(ConfigError::InvalidWebServerPort(self.url.clone()));
                }
                Ok(port)
            }
            None => {
                if trimmed.starts_with("https://") {
                    Ok(443)
                } else {
                    Ok(80)
                }
            }
        }
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

fn default_url() -> String {
    "http://0.0.0.0:8080".to_string()
}

fn default_prefix() -> String {
    "/api/angry-agent/v1".to_string()
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct AuthConfig {
    pub jwt_public_key: String,
    pub jwt_issuer: String,
    pub jwt_audience: String,
}

impl AuthConfig {
    pub fn validate(&self) -> Result<(), ConfigError> {
        if self.jwt_public_key.trim().is_empty() {
            return Err(ConfigError::InvalidAuthConfig(
                "jwt_public_key cannot be empty".to_string(),
            ));
        }
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

        // If secrets dir exists, load projected secrets
        if let Some(sec_dir) = secrets_path {
            if sec_dir.exists() && sec_dir.is_dir() {
                config.load_secrets(sec_dir)?;
            }
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

    #[test]
    fn webserver_port_parses_standard_and_path_suffixed_urls() {
        let cfg = WebServerConfig {
            url: "http://0.0.0.0:8080".to_string(),
            prefix: "/api".to_string(),
        };
        assert_eq!(cfg.port().unwrap(), 8080);

        let cfg_with_path = WebServerConfig {
            url: "http://0.0.0.0:8080/agent-be".to_string(),
            prefix: "/api/angry-agent/v1".to_string(),
        };
        assert_eq!(cfg_with_path.port().unwrap(), 8080);

        let cfg_https_with_query = WebServerConfig {
            url: "https://api.example.com:8443/agent-be?debug=1#frag".to_string(),
            prefix: "/api".to_string(),
        };
        assert_eq!(cfg_https_with_query.port().unwrap(), 8443);

        let cfg_ipv6 = WebServerConfig {
            url: "http://[::]:9090/agent-be".to_string(),
            prefix: "/api".to_string(),
        };
        assert_eq!(cfg_ipv6.port().unwrap(), 9090);

        let cfg_default_http = WebServerConfig {
            url: "http://example.com/agent-be".to_string(),
            prefix: "/api".to_string(),
        };
        assert_eq!(cfg_default_http.port().unwrap(), 80);

        let cfg_default_https = WebServerConfig {
            url: "https://example.com/agent-be".to_string(),
            prefix: "/api".to_string(),
        };
        assert_eq!(cfg_default_https.port().unwrap(), 443);
    }

    #[test]
    fn webserver_port_rejects_invalid_urls_and_ports() {
        for bad_url in [
            "",
            "0.0.0.0:8080",
            "ftp://0.0.0.0:8080",
            "http:///agent-be",
            "http://:8080/agent-be",
            "http://[::/agent-be",
        ] {
            let cfg = WebServerConfig {
                url: bad_url.to_string(),
                prefix: "/api".to_string(),
            };
            assert!(
                matches!(cfg.port(), Err(ConfigError::InvalidWebServerUrl(_))),
                "expected InvalidWebServerUrl for {bad_url:?}, got {:?}",
                cfg.port()
            );
        }

        for bad_port_url in [
            "http://0.0.0.0:0/agent-be",
            "http://0.0.0.0:99999/agent-be",
            "http://0.0.0.0:notaport/agent-be",
        ] {
            let cfg = WebServerConfig {
                url: bad_port_url.to_string(),
                prefix: "/api".to_string(),
            };
            assert!(
                matches!(cfg.port(), Err(ConfigError::InvalidWebServerPort(_))),
                "expected InvalidWebServerPort for {bad_port_url:?}, got {:?}",
                cfg.port()
            );
        }
    }

    #[test]
    fn validate_accepts_default_config() {
        let cfg = ServiceConfig::default();
        assert!(cfg.validate().is_ok());
    }

    #[test]
    fn validate_rejects_invalid_auth_config() {
        let cfg = ServiceConfig {
            auth: Some(AuthConfig {
                jwt_public_key: "   ".to_string(),
                jwt_issuer: "https://issuer".to_string(),
                jwt_audience: "aud".to_string(),
            }),
            ..Default::default()
        };
        assert!(matches!(
            cfg.validate(),
            Err(ConfigError::InvalidAuthConfig(_))
        ));

        let cfg_empty_issuer = ServiceConfig {
            auth: Some(AuthConfig {
                jwt_public_key: "key".to_string(),
                jwt_issuer: "".to_string(),
                jwt_audience: "aud".to_string(),
            }),
            ..Default::default()
        };
        assert!(matches!(
            cfg_empty_issuer.validate(),
            Err(ConfigError::InvalidAuthConfig(_))
        ));

        let cfg_empty_aud = ServiceConfig {
            auth: Some(AuthConfig {
                jwt_public_key: "key".to_string(),
                jwt_issuer: "https://issuer".to_string(),
                jwt_audience: " ".to_string(),
            }),
            ..Default::default()
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
            ..Default::default()
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
            ..Default::default()
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
            ..Default::default()
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
            ..Default::default()
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
