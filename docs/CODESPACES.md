# Codespaces workflow

## Existing Codespace: first repository update

The existing Codespace can contain an untracked CyberDune theme installed from
a ZIP, a changed Compose file and startup files. Save those changes before pulling:

```bash
cd /workspaces/CTFd
git status --short
git stash push --include-untracked -m "Before CyberDune repository update"
git pull --ff-only origin master
bash scripts/start-cyberdune.sh
docker compose restart ctfd
```

The local changes remain in the stash. Do not blindly run `git stash pop`: old
theme files can overwrite the updated theme or cause merge conflicts.
Inspect specific changes with `git stash show -p --include-untracked`.

### If an ignored theme blocks the pull

The old upstream `.gitignore` ignored custom themes, so `git stash -u` may not
save one installed from a ZIP. If Git reports that an existing theme would be
overwritten, preserve that theme outside the checkout, then retry:

```bash
cd /workspaces/CTFd
backup_root="/workspaces/cyberdune-before-pull-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup_root"
mv CTFd/themes/cyberdune "$backup_root/"
git pull --ff-only origin master
bash scripts/start-cyberdune.sh
docker compose restart ctfd
```

Move only the named theme directory. Leave `.data/`, uploads, other themes and
plugins in place. If another file blocks the pull, preserve that specific file
outside the checkout before retrying. Never use `git clean -fdx` or a hard reset
to solve this: those commands can discard data or edits.

If the branches have diverged, `--ff-only` stops. Review `git log --oneline --all
--graph -15` and preserve your local commits before choosing how to merge them.

## New dev container setup

The repository's `.devcontainer/devcontainer.json` adds the Docker-in-Docker
feature, forwards port 80 and runs the startup script through `postStartCommand`.
The Docker daemon runs in the Codespace, independently of Windows.

In an existing Codespace, pull the files first, then use **Codespaces: Rebuild
Container** to adopt the configuration. Rebuilding takes time; a fresh application
image may need to be built again. Keep event data under the existing `.data/`
bind-mounted directories, and export an event backup before replacing a Codespace.

New database? Complete `/setup`, then select the theme:

```bash
docker compose exec ctfd python scripts/activate-cyberdune.py
docker compose restart ctfd
```

## Routine update

```bash
cd /workspaces/CTFd
bash scripts/update-cyberdune.sh
```

For a theme edit, the bind mount makes the new files available immediately;
restarting CTFd refreshes its templates. For Dockerfile/dependency changes, rebuild
the application image with `docker compose up -d --build`.

## Diagnostics

```bash
docker compose ps
docker compose logs --tail=80 ctfd db nginx
curl -I --max-time 10 http://localhost:80
```

Use the **Ports** tab to open port 80. A successful running container alone does
not prove the web application is ready; database startup may take a little longer.
The startup helper retains the targeted legacy firewall workaround for the two
Compose subnets used by this project. It does not flush firewall rules.

## Official references

- [Introduction to dev containers](https://docs.github.com/en/codespaces/setting-up-your-project-for-codespaces/adding-a-dev-container-configuration/introduction-to-dev-containers)
- [Forwarding ports](https://docs.github.com/en/codespaces/developing-in-a-codespace/forwarding-ports-in-your-codespace)
- [Docker-in-Docker feature](https://github.com/devcontainers/features/tree/main/src/docker-in-docker)
