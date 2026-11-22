use hams::error::HamsError;
use hams::hams::config::HamsConfig;
use hams::hams::Hams;
use hams::probe::manual::Manual as ProbeManual;
use hams::probe::FFIProbe;
use std::net::SocketAddr;
use std::sync::atomic::{AtomicBool, Ordering};
use tracing::info;

pub struct HamsHandle {
    hams: Hams,
    ready_probe: ProbeManual,
    ready: AtomicBool,
}

impl HamsHandle {
    pub fn start(&mut self) -> Result<(), HamsError> {
        self.hams.start()
    }

    pub fn stop(&mut self) -> Result<(), HamsError> {
        self.hams.stop()
    }

    pub fn mark_ready(&self) {
        self.ready_probe.enable();
        self.ready.store(true, Ordering::Release);
    }

    pub fn mark_not_ready(&self) {
        self.ready_probe.disable();
        self.ready.store(false, Ordering::Release);
    }

    pub fn is_ready(&self) -> bool {
        self.ready.load(Ordering::Acquire)
    }
}

pub fn init_hams(hams_port: u16) -> Result<HamsHandle, HamsError> {
    let config = HamsConfig {
        name: env!("CARGO_PKG_NAME").to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        address: SocketAddr::from(([0, 0, 0, 0], hams_port)),
        ..Default::default()
    };

    info!(
        "Initializing HaMS for {} on {}",
        config.name, config.address
    );

    let mut hams = Hams::new(config);

    // Register initial liveness, readiness (starts false until boot completes), and startup probes
    let service_alive_probe = ProbeManual::new("agentrs-alive", true);
    hams.alive_insert(Box::new(FFIProbe::from(service_alive_probe)));

    let service_ready_probe = ProbeManual::new("agentrs-ready", false);
    hams.ready_insert(Box::new(FFIProbe::from(service_ready_probe.clone())));

    let startup_probe = ProbeManual::new("agentrs-startup", true);
    hams.startup_insert(Box::new(FFIProbe::from(startup_probe)));

    Ok(HamsHandle {
        hams,
        ready_probe: service_ready_probe,
        ready: AtomicBool::new(false),
    })
}
