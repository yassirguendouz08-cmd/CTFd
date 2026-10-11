# Start and stop the CYBERDUNE VPS

Run these scripts from Codespace, Oracle Cloud Shell, or another computer with Bash and authenticated OCI CLI. They cannot start a stopped VPS when stored only on that VPS.

```bash
bash start-vps.sh
bash stop-vps.sh
```

The scripts target `cyberdune-platform` in `af-casablanca-1` using its instance OCID. Start uses `START`; stop uses `SOFTSTOP` so Ubuntu can shut down gracefully. Neither script deletes the instance or its boot volume. The website is unavailable while stopped. Oracle may be unable to start an instance if capacity is unavailable; the scripts report API errors rather than claiming success.

They check the current state first, skip an already running/stopped instance, and wait up to ten minutes for completion. A timeout does not cancel an action already accepted by Oracle. OCI authentication errors stop execution before any power action.

## One-time setup in Codespace

Install OCI CLI in its own Python environment, separate from CTFd:

```bash
python3 -m venv ~/.local/share/cyberdune-oci
~/.local/share/cyberdune-oci/bin/python -m pip install oci-cli
~/.local/share/cyberdune-oci/bin/oci setup config
```

The setup asks for your Oracle **user OCID**, **tenancy OCID**, and region (`af-casablanca-1`). These differ from the instance OCID embedded in the scripts. Generate an API key pair when prompted. Upload only the generated **public API key** to your Oracle user's **API Keys** section. The VPS SSH key is a separate key and is not used for OCI API authentication.

Keep the CLI configuration and private API key in `~/.oci`, outside the repository. Do not upload private keys to GitHub or paste them in chat. Codespace credentials grant the permissions of the Oracle user associated with the API key.

Oracle Cloud Shell already provides OCI CLI and authentication, subject to your user's permissions; skip local CLI setup there.

## After starting

Docker and host Nginx are configured to start automatically on this VPS. Allow time for Ubuntu and containers to boot, then check `https://ctf.cyberdune.online/`. HTTPS certificate setup must have completed first.

For SSH diagnostics:

```bash
~/ctfd-compose ps
sudo systemctl status nginx --no-pager
curl --max-time 20 -I http://127.0.0.1:8000/
```

On this deployment, use `~/ctfd-compose` to preserve the production database settings. Host Nginx handles web traffic; keep the Compose `nginx` service stopped to avoid a port 80 conflict. Do not run an unrestricted `docker compose up -d`.

References: [OCI CLI setup](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm), [instance power commands](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/compute/instance/action.html), [Cloud Shell](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/cloudshellintro.htm).
