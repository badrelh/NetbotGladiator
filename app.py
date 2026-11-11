import typer
from DdosMonitor import run_ddos_monitoring
from defacement_detector import run_defacement_monitoring
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from Certif_Monitor import run_certifs_monitoring
from detector import run_ddos_detect


app = typer.Typer(help="NetBotGladiator: ddoS, defacement, certificats", add_completion=False)


def VerifyConfigFile(config: str, command_name: str):
    if not Path(config).exists():
        typer.echo(f"Error: Config file not found: {config}", err=True)
        typer.echo("Usage examples:", err=True)
        typer.echo(f"python3 app.py {command_name} -c Config/config.yaml ", err=True)
        raise typer.Exit(code=1)



@app.command("collector")
def cmd_collector(config: str = typer.Option("Config/ddos.yaml", "-c", help="Fichier config ")):
    VerifyConfigFile(config, "ddos")
    typer.echo("Starting collector service...\n")
    typer.echo(f"Using config file: {config}\n")
    run_ddos_monitoring(config)


@app.command("defacement")
def cmd_deface(config: str = typer.Option("Config/defacement.yaml", "-c", help="Fichier config ")):
    VerifyConfigFile(config, "defacement")
    typer.echo("Starting defacement service...\n")
    typer.echo(f"Using config file: {config}\n")
    run_defacement_monitoring(config)


@app.command("certificats")
def cmd_certs(config: str = typer.Option("Config/certs.yaml", "-c", help="Fichier config ")):
    VerifyConfigFile(config, "certificats")
    typer.echo("Starting certificate monitoring service...\n")
    typer.echo(f"Using config file: {config}\n")
    run_certifs_monitoring(config)

@app.command("ddos_detect")
def cmd_ddos_detect(config: str = typer.Option("Config/config.yaml", "-c", help="Fichier config ")):
    VerifyConfigFile(config, "ddos detect")
    typer.echo("Starting certificate monitoring service...\n")
    typer.echo(f"Using config file: {config}\n")
    run_ddos_detect(config)




@app.command("all")
def all(config: str = typer.Option("Config/config.yaml", "-c", help="Fichier config ")):
    VerifyConfigFile(config, "all")
    typer.echo("Starting ALL services...\n")
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(cmd_collector, config),
                executor.submit(cmd_deface, config),
                executor.submit(cmd_certs, config),
                executor.submit(cmd_ddos_detect, config)
            ]
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    typer.echo(f"Error: {e}", err=True)
    except KeyboardInterrupt:
        typer.echo("\n   Stopped", err=True)


if __name__ == "__main__":
    app()
