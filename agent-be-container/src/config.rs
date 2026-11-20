use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Deserialize, Serialize)]
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

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct PersistenceConfig {
    pub db: Option<DbConfig>,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct DbConfig {
    pub pool_size: Option<u32>,
    pub automigrate: Option<bool>,
    pub acquire_timeout: Option<u64>,
    pub connection: Option<DbConnectionConfig>,
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

impl ServiceConfig {
    pub fn from_yaml_and_secrets(
        yaml_path: &Path,
        secrets_path: Option<&Path>,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        let content = fs::read_to_string(yaml_path)?;
        let mut config: ServiceConfig = serde_yaml::from_str(&content)?;

        // If secrets dir exists, load projected secrets
        if let Some(sec_dir) = secrets_path {
            if sec_dir.exists() && sec_dir.is_dir() {
                config.load_secrets(sec_dir);
            }
        }

        Ok(config)
    }

    fn load_secrets(&mut self, secrets_dir: &Path) {
        // Look for persistence/db/connection/username and password
        let user_file = secrets_dir.join("persistence/db/connection/username");
        if user_file.exists() {
            if let Ok(u) = fs::read_to_string(user_file) {
                if let Some(ref mut p) = self.persistence {
                    if let Some(ref mut db) = p.db {
                        if let Some(ref mut conn) = db.connection {
                            conn.username = Some(u.trim().to_string());
                        }
                    }
                }
            }
        }

        let pass_file = secrets_dir.join("persistence/db/connection/password");
        if pass_file.exists() {
            if let Ok(p_str) = fs::read_to_string(pass_file) {
                if let Some(ref mut p) = self.persistence {
                    if let Some(ref mut db) = p.db {
                        if let Some(ref mut conn) = db.connection {
                            conn.password = Some(p_str.trim().to_string());
                        }
                    }
                }
            }
        }
    }
}
