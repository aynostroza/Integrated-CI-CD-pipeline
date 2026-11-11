# GitHub → ngrok → Jenkins → Webex lab

This package supplies the remaining code and a setup path for your existing Windows 11 machine, GitHub repository, and Linux Jenkins container. Use your existing repository:

https://github.com/aynostroza/Integrated-CI-CD-pipeline

**Prepared and locally tested:** a calculator application, 25 unit tests, build/test scripts, a Jenkins Pipeline, and a Webex notification script adapted from your example's Bearer-token / roomId / messages API approach. The build produces a runnable Python ZIP application, then Jenkins tests it and archives the artifact.

**Still to complete on your computer:** install any missing Jenkins tools/plugins, create the Webex bot and credentials, start ngrok, configure the job and webhook, run a live test, and record the result. This package does not claim that those account or local-machine changes have already happened. GitHub reported a connected account, but repository-reading tools were not exposed to this session; the repository contents were not verified or changed.

Everything is under `ci_lab/` so you can add the lab without replacing root-level files already in your repository. The Pipeline below builds and tests the supplied calculator and notification code. It does not automatically run unknown tests from your existing project. If `ci_lab/` already exists in your checkout, compare the files before copying.

## 1. Add the files to your local repository

Extract the downloaded ZIP. Copy its **ci_lab folder** into the top level of your existing local repository. Do not create a second Git repository inside it. Your repository should now contain `ci_lab/Jenkinsfile`, `ci_lab/build.sh`, `ci_lab/test.sh`, `ci_lab/webex_notify.py`, and the `app` and `tests` subfolders.

Open PowerShell in the repository folder. Replace the example path below with your actual folder:

```powershell
Set-Location "C:\path\to\Integrated-CI-CD-pipeline"
git status
git remote -v
git branch --show-current
```

The instructions assume `main`. If your branch has another name, substitute it both in the push command and the Jenkins branch setting later. `origin` should point to your existing GitHub repository. Save any files you edited before running Git commands.

```powershell
git add ci_lab
git diff --cached --stat
git commit -m "Add Jenkins build, unit tests, and Webex notifications"
git push origin main
```

If Git says `nothing to commit, working tree clean`, verify that you copied/saved the files inside this repository and that `git status --short` shows a change. A local commit does not trigger GitHub: **git push is the step that sends the commit to GitHub and causes a push event.**

## 2. Check your existing Jenkins container

Keep Docker Desktop running with Linux containers. In PowerShell:

```powershell
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}"
```

All following commands use `jenkins` as the container name. Replace it with the name shown above. The instructions use host port `8080`; if the port mapping is `8081->8080`, use `8081` for the browser and ngrok instead.

Open http://localhost:8080 and sign in. Check the tools inside the container:

```powershell
docker exec jenkins python3 --version
docker exec jenkins git --version
docker exec jenkins cat /etc/os-release
```

If Python or Git is missing and the image is Debian/Ubuntu based (as the standard Jenkins Debian image is), run:

```powershell
docker exec -u 0 jenkins sh -c "apt-get update && apt-get install -y python3 git ca-certificates"
```

The application uses Python 3.9 or newer and only its standard library. No pip, virtual environment, requests package, or Docker daemon inside Jenkins is needed. An Alpine-based image uses a different package manager; for that image the equivalent is `docker exec -u 0 jenkins apk add --no-cache python3 git ca-certificates`.

The package installation above persists across container restarts, but not deletion/recreation. `ci_lab/Dockerfile.jenkins` is an optional image definition for a future reproducible rebuild; it is not needed for this existing-container route. Keep your current Jenkins data volume and configuration. Do not delete/recreate your container just to follow this lab.

In **Manage Jenkins → Plugins**, install or confirm these plugins and their dependencies:

| Plugin | Purpose |
|---|---|
| Pipeline (including Declarative Pipeline) | Runs the Jenkinsfile |
| Git | Checks out the repository |
| GitHub | Receives GitHub push events |
| Credentials Binding | Makes the bot credentials available only during notification |
| Timestamper | Adds readable timestamps to the console log |

Restart Jenkins after installation if prompted, when no build is running.

In **Manage Jenkins → Nodes → Built-In Node → Configure**, add the label **linux-python** and ensure **Number of executors** is at least **1**. Keep any existing labels. This lets the supplied Pipeline select your Linux container. Running on the controller is adequate for this personal lab; a shared production server should use a separate agent. If you already have a Linux agent with Python installed, apply the label there instead.

Before recording, confirm Jenkins requires a login and anonymous users cannot administer it. Keep CSRF protection enabled.

## 3. Create the Webex bot and find the room ID

1. Sign in at https://developer.webex.com/ using your Webex account.
2. Open **My Webex Apps → Create a New App → Create a Bot**.
3. Give it a name such as `JenkinsLabBot`, a unique bot username, an icon, and a description. Create it.
4. Save the **bot access token** privately and copy the bot's email address. Use the bot token, not a short-lived personal developer token.
5. In the Webex application, create or choose a space named **CI-CD Build Notifications**.
6. Add the bot to that space using its bot email address. Your own Webex account should also be a member.

Your old ISS bot code polls for incoming commands. This lab only needs Jenkins to send an outbound status message. The supplied script sends one message and exits; you do not need to run the old polling loop or configure a Webex webhook.

Use the provided script to list the spaces this bot can see. From PowerShell in your local repository:

```powershell
docker cp .\ci_lab jenkins:/tmp/ci_lab
docker exec -it jenkins python3 /tmp/ci_lab/webex_notify.py list-rooms
```

At the hidden prompt, paste the bot token **without** `Bearer `, then press Enter. The prompt does not echo the token. Find **CI-CD Build Notifications** and copy its **Room ID**. The ID is not the room's display name. If no rooms appear, add the bot's email address to the space and try again. The helper follows API pagination.

An alternative, if Python is installed on Windows, is:

```powershell
py -3 ci_lab/webex_notify.py list-rooms
```

Do not put your bot token in a Python file, Git commit, screenshot, or recording.

## 4. Store the credentials in Jenkins

Open **Manage Jenkins → Credentials → System → Global credentials (unrestricted) → Add Credentials**. Menu wording may vary slightly. Create these two credentials, both with **Kind = Secret text** and **Scope = Global**:

| ID — enter exactly | Secret value |
|---|---|
| `webex-bot-token` | Your Webex bot access token, without `Bearer ` |
| `webex-room-id` | The Room ID returned by the helper |

Create a third Secret text credential for webhook signature verification:

| ID | Secret value |
|---|---|
| `github-webhook-secret` | A random value you generate once and use in both Jenkins and GitHub |

You can generate that value before recording with:

```powershell
docker exec jenkins python3 -c "import secrets; print(secrets.token_hex(32))"
```

In **Manage Jenkins → System → GitHub**, expand **Advanced** and locate **Shared secrets / Add shared secret**. Select `github-webhook-secret`. If a signature-algorithm setting is displayed, select **SHA-256**. Save. The exact placement varies by GitHub plugin version; update the GitHub plugin if this setting is missing. Do not confuse this with the GitHub Server API credential field. The shared secret must match the Secret field of the repository webhook you will create in step 7.

You will create the webhook manually. A public repository can be checked out without a GitHub PAT, and automatic GitHub hook management does not need to be enabled.

## 5. Start ngrok on Windows

Install the Windows CLI using https://ngrok.com/download/windows and sign in to an ngrok account. Open a separate PowerShell window. Perform token configuration before recording:

```powershell
ngrok config add-authtoken "PASTE_YOUR_NGROK_AUTHTOKEN_HERE"
```

Clear that terminal or open a new window before the recording, then run:

```powershell
ngrok http 8080
```

Leave this foreground window open so incoming webhook requests are visible. Use your published Windows host port if it is different. This command is run on Windows, where `localhost:8080` reaches the Docker-published Jenkins port.

Copy the exact **HTTPS Forwarding URL** printed by ngrok. It may resemble `https://your-domain.ngrok-free.dev`; use your actual URL, not this example.

In **Manage Jenkins → System → Jenkins Location**, set **Jenkins URL** to that HTTPS address with a final `/`. This makes the build link in the Webex message reachable through the tunnel. If the forwarding URL ever changes, update both Jenkins URL and the GitHub webhook URL.

You can inspect request details at http://localhost:4040. Keep ngrok running until you finish the demo. Do not add a separate browser login challenge to the webhook path: GitHub must be able to POST to it. Jenkins's normal login and the webhook signature protect their respective endpoints.

## 6. Create the Jenkins Pipeline job

In Jenkins select **New Item**, name it **Integrated-CI-CD-pipeline**, select **Pipeline**, then configure:

| Setting | Value |
|---|---|
| GitHub project, if shown | `https://github.com/aynostroza/Integrated-CI-CD-pipeline/` |
| Build trigger | Check **GitHub hook trigger for GITScm polling** |
| Definition | **Pipeline script from SCM** |
| SCM | **Git** |
| Repository URL | `https://github.com/aynostroza/Integrated-CI-CD-pipeline.git` |
| Credentials | **None** for this public repository |
| Branch Specifier | `*/main` (or your actual branch) |
| Script Path | **`ci_lab/Jenkinsfile`** |

Do not add scheduled Poll SCM or Build periodically triggers. The `githubPush()` declaration in the Jenkinsfile also configures the push trigger after its first run.

Save and click **Build Now once** to initialize the Pipeline and register its checkout and trigger. This first manual build is setup, not your recorded proof of automatic triggering.

Open **Console Output**. A successful baseline should show:

```text
BUILD PASSED: ci_lab/dist/calculator.pyz
...
Ran 25 tests in ...
OK
ALL PYTHON UNIT TESTS PASSED
...
Webex notification sent successfully.
Finished: SUCCESS
```

These are expected markers, not a claim that your Jenkins run has already occurred. Confirm the actual baseline message appears in Webex before continuing.

Pipeline stages are **Checkout → Build → Unit tests → Archive artifact**. The Build stage checks Python syntax, packages a runnable calculator, and smoke-tests that package. The tests exercise arithmetic and mock the Webex API, so unit tests do not send real messages. The `post` step sends the one live result.

Jenkins archives `calculator.pyz` on successful tests. Download it from the build's artifacts and run it with Python if desired, for example `py -3 calculator.pyz multiply 6 7`, which prints `42`. The lab requires build/test/notify automation, so there is no application hosting/deployment stage.

## 7. Add the GitHub push webhook

Open your repository's **Settings → Webhooks → Add webhook**:

| Field | Value |
|---|---|
| Payload URL | Your exact ngrok HTTPS address plus **`/github-webhook/`** |
| Content type | **`application/json`** |
| Secret | The same random value stored as `github-webhook-secret` in Jenkins |
| SSL verification | **Enabled** |
| Events | **Just the push event** |
| Active | **Checked** |

Example only: `https://your-domain.ngrok-free.dev/github-webhook/`. Keep the trailing slash. Do not use the job's `/build` URL or localhost as the payload URL.

Save. GitHub sends a `ping` delivery; check **Recent Deliveries** for a successful HTTP response. A ping proves delivery but is not a code-push build. If it fails, fix delivery before recording. A subsequent push to the configured branch should cause Jenkins to build.

## 8. Rehearse the complete live pipeline

Make a harmless code change in `ci_lab/app/calculator.py`, such as adding a comment beneath the module docstring. Save it and run:

```powershell
git diff -- ci_lab/app/calculator.py
git add ci_lab/app/calculator.py
git commit -m "Verify automatic Jenkins build and Webex notification"
git push origin main
```

Wait for the new build without clicking Build Now. Verify the new GitHub commit, ngrok POST, Jenkins trigger/cause, passing tests, final SUCCESS, and the Webex message. The full commit SHA printed by Jenkins should match the SHA in the notification and GitHub commit. A green GitHub webhook delivery alone does not prove a job ran.

Optional failure test: temporarily change the expected result of `test_add_positive` from `5` to `6`, commit and push it, then confirm the test stage fails and Webex reports FAILURE. Immediately restore `5`, commit and push again, and confirm SUCCESS. The requested submission needs the successful demonstration; the failure test is extra practice, not part of the required recording.

If Webex delivery fails after otherwise successful build/tests, the Jenkinsfile makes the job **UNSTABLE**, not a misleading green success. An already failed build stays **FAILURE**. The message labels the result as **build/tests** because notification delivery is a separate final action. A checkout failure before the notification script is available, or an unavailable node, can prevent a notification; the console reports that limitation when possible.

## 9. Record the submission — 80 points

Finish all credential setup before recording. Open the local editor/PowerShell, GitHub repository page, foreground ngrok terminal, Jenkins job page, and Webex space. Use a recorder that captures the whole display so terminal and browser switches are visible. Keep font sizes readable and account tokens out of the recording.

Start with a completed baseline build. Then record one continuous successful run:

| Order | Show on screen | Rubric |
|---|---|---|
| 1 | Add a new comment in `ci_lab/app/calculator.py`, save, show `git diff`, `git add`, `git commit`, and `git push` | Required demonstration |
| 2 | Refresh GitHub immediately; show your new commit message and its relative timestamp (`now`, `just now`, or seconds ago) | 10 points |
| 3 | Show the **ngrok terminal** receiving `POST /github-webhook/` and the successful response; optionally also show the matching request at localhost:4040 | 20 points |
| 4 | Show Jenkins starting the new build automatically and its GitHub push cause. Do not click Build Now | 20 points |
| 5 | Open Console Output; show the commit SHA, build stage, verbose test names, `Ran 25 tests`, `OK`, and `Finished: SUCCESS` | 20 points |
| 6 | Open the Webex space; show the bot's SUCCESS message with matching job, build number, commit SHA, and results link | 10 points |

For the recording, use a fresh comment such as `# Recording demonstration: automatic build from a GitHub push.` If that exact change was already committed during practice, use a different comment so Git has a new change to commit.

Suggested narration: “I am pushing a code change to GitHub. GitHub sends a push webhook to the ngrok URL. ngrok forwards it to Jenkins, which checks out the commit, builds the application, and runs all unit tests. The Webex bot then posts the build result to this space.”

Before submitting, play back the recording and verify all six items are visible and readable. Do not substitute the baseline manual run for the automatically triggered demonstration. Submit the recording through your course's required submission page.

## Troubleshooting

| Symptom | What to check |
|---|---|
| `fatal: not a git repository` | Open PowerShell inside your existing cloned repository, not the extracted ZIP folder. |
| `nothing to commit, working tree clean` | Save a new edit, check your current directory and `git diff`, then stage the specific changed file. |
| Push rejected because remote has new commits | Commit your own changes first, run `git pull --rebase origin main`, resolve any conflict, then push. Do not force-push over work. |
| `python3: not found` in Jenkins | Install Python inside the Linux container/node; installing it only on Windows does not install it in Jenkins. |
| `apt-get: not found` | Check `/etc/os-release`; an Alpine image uses `apk` instead. |
| `Waiting for next available executor` | Check the `linux-python` label, at least one executor, and node online state. |
| Jenkins cannot find the Jenkinsfile | Confirm the pushed branch contains `ci_lab/Jenkinsfile`, and set Script Path to that exact path. |
| `No such DSL method githubPush` | Install/update the GitHub plugin and restart Jenkins if needed. |
| `Invalid option type timestamps` | Install Timestamper. |
| Missing credential ID | Create Global Secret text entries named exactly `webex-bot-token` and `webex-room-id`. |
| ngrok shows connection refused / 502 | Confirm Jenkins opens on Windows at the host port you passed to ngrok. |
| GitHub hook 404 | Check forwarding domain, plugin installation, and `/github-webhook/` path. |
| GitHub hook 403 / signature failure | Match the webhook secret on both sides; keep the trailing slash and normal Jenkins CSRF protection. |
| Hook responds 200 but no build | Confirm a real push to the configured branch, GitHub trigger enabled, matching SCM URL, and a completed first manual run. Redelivering an already-built commit may not start another build. |
| Webex 401 | Use the current bot token without `Bearer `, and update Jenkins credentials if regenerated. |
| Webex 403 / 404 | Add the bot to the correct space, confirm it may post there, and use that space's Room ID. |
| Webex 429 | Wait for the rate limit to clear and retry. The script does not blindly retry POST requests that could duplicate messages. |
| Webex network/TLS error | Check container internet, DNS, firewall/proxy, and trusted certificate configuration. TLS verification stays enabled. |
| `bash\r`, `$'\r'`, or shell syntax error | Shell scripts must use LF line endings. The supplied `.gitattributes` enforces LF in fresh checkouts; run `git add --renormalize ci_lab`, commit, and push if needed. |
| Notification link fails later | Keep ngrok running and Jenkins URL current; a tunnel URL works only while its endpoint is available. |
| Jenkins finishes UNSTABLE | Inspect the notification step. A delivery problem must be fixed before recording a complete SUCCESS run. |

## Validation and references

Local validation completed for the provided package: build script passed, calculator artifact ran, all 25 unit tests passed, and the notifier's API behavior was tested with mocks. Jenkins itself, your Docker container, ngrok delivery, your bot credentials, and the full live chain could not be exercised from this session. Your first manual baseline and subsequent push-triggered rehearsal validate those parts.

Official references used for the setup:

- Jenkins GitHub plugin and push trigger: https://plugins.jenkins.io/github/
- Jenkins Pipeline syntax: https://www.jenkins.io/doc/book/pipeline/syntax/
- Jenkins credentials binding: https://www.jenkins.io/doc/pipeline/steps/credentials-binding/
- Jenkins Docker installation: https://www.jenkins.io/doc/book/installing/docker/
- GitHub webhook setup: https://docs.github.com/en/webhooks/using-webhooks/creating-webhooks
- ngrok CLI quickstart: https://ngrok.com/docs/gateway/endpoints/agent-cli-quickstart
- ngrok request inspector: https://ngrok.com/docs/gateway/agent/web-inspection-interface
- Webex bots: https://developer.webex.com/create/docs/bots
- Webex message API: https://developer.webex.com/messaging/docs/api/v1/messages/create-a-message
