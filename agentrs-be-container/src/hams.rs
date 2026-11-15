use hams::hams::config::HamsConfig;
use hams::hams::Hams;
use hams::probe::manual::Manual as ProbeManual;
use hams::probe::FFIProbe;
use std::net::SocketAddr;
use tracing::info;

pub fn init_hams(hams_port: u16) -> Result<Hams, Box<dyn std::error::Error + Send + Sync>> {
    let mut config = HamsConfig::default();
    config.name = env!("CARGO_PKG_NAME").to_string();
    config.version = env!("CARGO_PKG_VERSION").to_string();
    config.address = SocketAddr::from(([0, 0, 0, 0], hams_port));

    info!("Initializing HaMS for {} on {}", config.name, config.address);

    let mut hams = Hams::new(config);

    // Register initial liveness and readiness manual probes
    let service_alive_probe = ProbeManual::new("agentrs-alive", true);
    hams.alive_insert(Box::new(FFIProbe::from(service_alive_probe)));

    let service_ready_probe = ProbeManual::new("agentrs-ready", true);
    hams.ready_insert(Box::new(FFIProbe::from(service_ready_probe)));

    let startup_probe = ProbeManual::new("agentrs-startup", true);
    hams.startup_insert(Box::new(FFIProbe::from(startup_probe)));

    Ok(hams)
}
