use clap::{Parser, Subcommand, ValueEnum};
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(
    name = "agentrs-be",
    version,
    about = "Angry Agent Rust Backend Service"
)]
pub struct Cli {
    #[arg(long, default_value = "false")]
    pub debug: bool,

    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand, Debug, PartialEq, Eq)]
pub enum Commands {
    /// Start the web server and background services
    Start {
        #[arg(long)]
        config: PathBuf,
        #[arg(long)]
        secrets: Option<PathBuf>,
    },
    /// Run database schema migrations
    Migrate {
        #[arg(long, value_enum, default_value_t = MigrationAction::Apply)]
        action: MigrationAction,
        #[arg(long)]
        config: PathBuf,
        #[arg(long)]
        secrets: Option<PathBuf>,
    },
}

#[derive(ValueEnum, Clone, Copy, Debug, PartialEq, Eq)]
pub enum MigrationAction {
    Apply,
    Rollback,
    List,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_start_subcommand() {
        let cli = Cli::try_parse_from([
            "agentrs-be",
            "start",
            "--config",
            "/opt/app/configs/config.yaml",
            "--secrets",
            "/opt/app/secrets",
        ])
        .expect("start subcommand should parse");

        assert_eq!(
            cli.command,
            Commands::Start {
                config: PathBuf::from("/opt/app/configs/config.yaml"),
                secrets: Some(PathBuf::from("/opt/app/secrets")),
            }
        );
    }

    #[test]
    fn parses_migrate_subcommand_defaults_to_apply() {
        let cli = Cli::try_parse_from([
            "agentrs-be",
            "migrate",
            "--config",
            "/opt/app/configs/config.yaml",
        ])
        .expect("migrate subcommand should parse");

        assert_eq!(
            cli.command,
            Commands::Migrate {
                action: MigrationAction::Apply,
                config: PathBuf::from("/opt/app/configs/config.yaml"),
                secrets: None,
            }
        );
    }

    #[test]
    fn parses_migrate_rollback_and_list() {
        let rollback = Cli::try_parse_from([
            "agentrs-be",
            "migrate",
            "--action",
            "rollback",
            "--config",
            "/opt/app/configs/config.yaml",
        ])
        .expect("migrate rollback should parse");
        assert_eq!(
            rollback.command,
            Commands::Migrate {
                action: MigrationAction::Rollback,
                config: PathBuf::from("/opt/app/configs/config.yaml"),
                secrets: None,
            }
        );

        let list = Cli::try_parse_from([
            "agentrs-be",
            "migrate",
            "--action",
            "list",
            "--config",
            "/opt/app/configs/config.yaml",
        ])
        .expect("migrate list should parse");
        assert_eq!(
            list.command,
            Commands::Migrate {
                action: MigrationAction::List,
                config: PathBuf::from("/opt/app/configs/config.yaml"),
                secrets: None,
            }
        );
    }

    #[test]
    fn rejects_missing_subcommand_or_missing_config() {
        assert!(Cli::try_parse_from(["agentrs-be"]).is_err());
        assert!(Cli::try_parse_from(["agentrs-be", "start"]).is_err());
        assert!(Cli::try_parse_from(["agentrs-be", "migrate"]).is_err());
    }
}
