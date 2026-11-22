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
    pub command: Option<Commands>,

    /// Fallback option for running directly with --config
    #[arg(long)]
    pub config: Option<PathBuf>,

    /// Fallback option for running directly with --secrets
    #[arg(long)]
    pub secrets: Option<PathBuf>,
}

#[derive(Subcommand, Debug, PartialEq, Eq)]
pub enum Commands {
    /// Start the web server and background services
    Start {
        #[arg(long)]
        config: Option<PathBuf>,
        #[arg(long)]
        secrets: Option<PathBuf>,
    },
    /// Run database schema migrations
    Migrate {
        #[arg(long, value_enum, default_value_t = MigrationAction::Apply)]
        action: MigrationAction,
        #[arg(long)]
        config: Option<PathBuf>,
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
            Some(Commands::Start {
                config: Some(PathBuf::from("/opt/app/configs/config.yaml")),
                secrets: Some(PathBuf::from("/opt/app/secrets")),
            })
        );
    }

    #[test]
    fn parses_migrate_subcommand_defaults_to_apply() {
        let cli = Cli::try_parse_from(["agentrs-be", "migrate"])
            .expect("migrate subcommand should parse");

        assert_eq!(
            cli.command,
            Some(Commands::Migrate {
                action: MigrationAction::Apply,
                config: None,
                secrets: None,
            })
        );
    }

    #[test]
    fn parses_migrate_rollback_and_list() {
        let rollback = Cli::try_parse_from(["agentrs-be", "migrate", "--action", "rollback"])
            .expect("migrate rollback should parse");
        assert_eq!(
            rollback.command,
            Some(Commands::Migrate {
                action: MigrationAction::Rollback,
                config: None,
                secrets: None,
            })
        );

        let list = Cli::try_parse_from(["agentrs-be", "migrate", "--action", "list"])
            .expect("migrate list should parse");
        assert_eq!(
            list.command,
            Some(Commands::Migrate {
                action: MigrationAction::List,
                config: None,
                secrets: None,
            })
        );
    }

    #[test]
    fn parses_top_level_fallback_args() {
        let cli = Cli::try_parse_from([
            "agentrs-be",
            "--debug",
            "--config",
            "config.yaml",
            "--secrets",
            "secrets",
        ])
        .expect("fallback args should parse");

        assert!(cli.debug);
        assert!(cli.command.is_none());
        assert_eq!(cli.config, Some(PathBuf::from("config.yaml")));
        assert_eq!(cli.secrets, Some(PathBuf::from("secrets")));
    }
}
