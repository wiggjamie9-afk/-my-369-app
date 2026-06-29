#!/usr/bin/env bash
#
# install-clis.sh
# -----------------------------------------------------------------------------
# Installs the command-line tools for the subset of services in
# awesome-free-services.md that actually ship a CLI.
#
# IMPORTANT: Installing a CLI does NOT create an account or log you in.
# Almost every tool below needs you to (1) sign up on the provider's website
# and (2) run its `login`/`auth` command before it does anything useful.
# A reminder of the login command is printed for each tool at the end.
#
# Usage:
#   ./install-clis.sh            # install everything (incl. heavy cloud SDKs)
#   ./install-clis.sh --core     # skip the large cloud SDKs (aws/gcloud/az/oci/ibm)
#   ./install-clis.sh --list     # just list what would be installed, do nothing
#   ./install-clis.sh -h         # help
#
# Supported OS: Linux and macOS. Re-running is safe — anything already
# installed is skipped.
# -----------------------------------------------------------------------------

set -u  # treat unset vars as errors; we deliberately do NOT use -e so one
        # failed install can't abort the whole run.

# ----- pretty output ---------------------------------------------------------
if [ -t 1 ]; then
  BOLD=$'\033[1m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; DIM=$'\033[2m'; RESET=$'\033[0m'
else
  BOLD=""; GREEN=""; YELLOW=""; RED=""; DIM=""; RESET=""
fi

INSTALLED=()
SKIPPED=()
FAILED=()
LOGIN_HINTS=()

info()  { printf '%s\n' "${BOLD}==>${RESET} $*"; }
ok()    { printf '%s\n' "  ${GREEN}ok${RESET}   $*"; }
warn()  { printf '%s\n' "  ${YELLOW}warn${RESET} $*"; }
err()   { printf '%s\n' "  ${RED}fail${RESET} $*"; }

# ----- OS / package manager detection ---------------------------------------
OS="unknown"
case "$(uname -s)" in
  Linux*)  OS="linux" ;;
  Darwin*) OS="macos" ;;
esac

HAS_BREW=0;   command -v brew   >/dev/null 2>&1 && HAS_BREW=1
HAS_NPM=0;    command -v npm    >/dev/null 2>&1 && HAS_NPM=1
HAS_CURL=0;   command -v curl   >/dev/null 2>&1 && HAS_CURL=1
HAS_APT=0;    command -v apt-get>/dev/null 2>&1 && HAS_APT=1

# ----- args ------------------------------------------------------------------
CORE_ONLY=0
LIST_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --core|--core-only) CORE_ONLY=1 ;;
    --list)             LIST_ONLY=1 ;;
    -h|--help)
      sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) warn "unknown option: $arg (ignored)" ;;
  esac
done

# ----- helpers ---------------------------------------------------------------
# already_installed <command-name>
already_installed() { command -v "$1" >/dev/null 2>&1; }

# record_login "<tool>" "<login command>"
record_login() { LOGIN_HINTS+=("$1|$2"); }

# run_install <pretty-name> <command-to-test> <login-hint> <install-cmd...>
# The install command is passed as a single string evaluated by the shell.
attempt() {
  local name="$1" testcmd="$2" login="$3" installcmd="$4"
  if already_installed "$testcmd"; then
    ok "$name already installed ($(command -v "$testcmd"))"
    SKIPPED+=("$name")
    [ -n "$login" ] && record_login "$name" "$login"
    return 0
  fi
  if [ "$LIST_ONLY" -eq 1 ]; then
    printf '%s\n' "  would install ${BOLD}$name${RESET} ${DIM}-> $installcmd${RESET}"
    return 0
  fi
  info "installing $name"
  if eval "$installcmd" >/tmp/cli_install_$$.log 2>&1; then
    ok "$name installed"
    INSTALLED+=("$name")
    [ -n "$login" ] && record_login "$name" "$login"
  else
    err "$name failed — see detail below"
    sed 's/^/      /' /tmp/cli_install_$$.log | tail -n 6
    FAILED+=("$name")
  fi
  rm -f /tmp/cli_install_$$.log
}

# npm global install wrapper (most JS-based CLIs)
npm_install() { # <pretty> <bin> <login> <npm-package>
  if [ "$HAS_NPM" -ne 1 ]; then
    warn "$1 skipped — npm not found (install Node.js first: https://nodejs.org)"
    FAILED+=("$1 (no npm)")
    return 1
  fi
  attempt "$1" "$2" "$3" "npm install -g $4"
}

# ----- preflight -------------------------------------------------------------
info "Detected OS: ${BOLD}$OS${RESET}  |  npm:$HAS_NPM brew:$HAS_BREW curl:$HAS_CURL apt:$HAS_APT"
if [ "$OS" = "unknown" ]; then
  warn "Unsupported OS. This script targets Linux and macOS."
fi
if [ "$HAS_NPM" -ne 1 ]; then
  warn "npm not found — the JavaScript-based CLIs (vercel, netlify, wrangler, surge) will be skipped."
  warn "Install Node.js from https://nodejs.org or your package manager, then re-run."
fi
echo

# =============================================================================
# 1) JavaScript / npm-based CLIs
# =============================================================================
info "${BOLD}Web hosting & edge platforms (npm)${RESET}"
npm_install "Vercel"       "vercel"  "vercel login"        "vercel"
npm_install "Netlify"      "netlify" "netlify login"       "netlify-cli"
npm_install "Cloudflare Wrangler" "wrangler" "wrangler login" "wrangler"
npm_install "Surge.sh"     "surge"   "surge login"         "surge"
echo

# =============================================================================
# 2) Standalone developer CLIs (official installers)
# =============================================================================
info "${BOLD}Developer & infra CLIs${RESET}"

# GitHub CLI
if [ "$HAS_BREW" -eq 1 ]; then
  attempt "GitHub CLI" "gh" "gh auth login" "brew install gh"
elif [ "$HAS_APT" -eq 1 ]; then
  attempt "GitHub CLI" "gh" "gh auth login" \
    "sudo apt-get update && sudo apt-get install -y gh || (curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && echo 'deb [signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main' | sudo tee /etc/apt/sources.list.d/github-cli.list && sudo apt-get update && sudo apt-get install -y gh)"
else
  warn "GitHub CLI skipped — need brew or apt. See https://github.com/cli/cli#installation"
  FAILED+=("GitHub CLI (no pkg mgr)")
fi

# Tailscale
if [ "$OS" = "macos" ] && [ "$HAS_BREW" -eq 1 ]; then
  attempt "Tailscale" "tailscale" "tailscale up" "brew install tailscale"
elif [ "$OS" = "linux" ] && [ "$HAS_CURL" -eq 1 ]; then
  attempt "Tailscale" "tailscale" "sudo tailscale up" "curl -fsSL https://tailscale.com/install.sh | sh"
else
  warn "Tailscale skipped — see https://tailscale.com/download"
  FAILED+=("Tailscale")
fi

# ngrok
if [ "$HAS_BREW" -eq 1 ]; then
  attempt "ngrok" "ngrok" "ngrok config add-authtoken <TOKEN>" "brew install ngrok/ngrok/ngrok"
elif [ "$OS" = "linux" ] && [ "$HAS_CURL" -eq 1 ]; then
  attempt "ngrok" "ngrok" "ngrok config add-authtoken <TOKEN>" \
    "curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && echo 'deb https://ngrok-agent.s3.amazonaws.com buster main' | sudo tee /etc/apt/sources.list.d/ngrok.list && sudo apt-get update && sudo apt-get install -y ngrok"
else
  warn "ngrok skipped — see https://ngrok.com/download"
  FAILED+=("ngrok")
fi

# Supabase CLI
if [ "$HAS_BREW" -eq 1 ]; then
  attempt "Supabase" "supabase" "supabase login" "brew install supabase/tap/supabase"
elif [ "$HAS_NPM" -eq 1 ]; then
  # supabase recommends not using npm -g, but it works for many setups
  attempt "Supabase" "supabase" "supabase login" "npm install -g supabase"
else
  warn "Supabase skipped — see https://supabase.com/docs/guides/cli"
  FAILED+=("Supabase")
fi

# DigitalOcean doctl
if [ "$HAS_BREW" -eq 1 ]; then
  attempt "DigitalOcean doctl" "doctl" "doctl auth init" "brew install doctl"
elif [ "$OS" = "linux" ] && [ "$HAS_CURL" -eq 1 ]; then
  attempt "DigitalOcean doctl" "doctl" "doctl auth init" \
    "cd /tmp && curl -sL https://github.com/digitalocean/doctl/releases/download/v1.104.0/doctl-1.104.0-linux-amd64.tar.gz | tar -xzv && sudo mv doctl /usr/local/bin"
else
  warn "doctl skipped — see https://docs.digitalocean.com/reference/doctl/how-to/install/"
  FAILED+=("doctl")
fi

# Deno + Deno Deploy (deployctl)
if [ "$HAS_BREW" -eq 1 ]; then
  attempt "Deno" "deno" "deployctl deploy" "brew install deno"
elif [ "$HAS_CURL" -eq 1 ]; then
  attempt "Deno" "deno" "deployctl deploy" "curl -fsSL https://deno.land/install.sh | sh"
fi
if already_installed deno; then
  attempt "Deno Deploy (deployctl)" "deployctl" "deployctl deploy" "deno install -gArf jsr:@deno/deployctl"
fi

# Sentry CLI (crash/exception handling)
if [ "$HAS_CURL" -eq 1 ]; then
  attempt "Sentry CLI" "sentry-cli" "sentry-cli login" "curl -sL https://sentry.io/get-cli/ | bash"
fi

# Doppler (secrets manager)
if [ "$HAS_BREW" -eq 1 ]; then
  attempt "Doppler" "doppler" "doppler login" "brew install dopplerhq/cli/doppler"
elif [ "$HAS_CURL" -eq 1 ]; then
  attempt "Doppler" "doppler" "doppler login" \
    "curl -Ls https://cli.doppler.com/install.sh | sudo sh"
fi

# Infisical (secrets manager)
if [ "$HAS_BREW" -eq 1 ]; then
  attempt "Infisical" "infisical" "infisical login" "brew install infisical/get-cli/infisical"
elif [ "$OS" = "linux" ] && [ "$HAS_CURL" -eq 1 ]; then
  attempt "Infisical" "infisical" "infisical login" \
    "curl -1sLf 'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.deb.sh' | sudo -E bash && sudo apt-get install -y infisical"
fi
echo

# =============================================================================
# 3) Big cloud-provider SDKs (skipped with --core)
# =============================================================================
if [ "$CORE_ONLY" -eq 1 ]; then
  info "${DIM}Skipping large cloud SDKs (--core). Run without --core to include aws/gcloud/az/oci/ibmcloud.${RESET}"
else
  info "${BOLD}Major cloud provider SDKs${RESET} ${DIM}(large; use --core to skip)${RESET}"

  # AWS CLI v2
  if [ "$HAS_BREW" -eq 1 ]; then
    attempt "AWS CLI" "aws" "aws configure" "brew install awscli"
  elif [ "$OS" = "linux" ] && [ "$HAS_CURL" -eq 1 ]; then
    attempt "AWS CLI" "aws" "aws configure" \
      "cd /tmp && curl -s 'https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip' -o awscliv2.zip && unzip -q -o awscliv2.zip && sudo ./aws/install --update"
  else
    warn "AWS CLI skipped — see https://aws.amazon.com/cli/"
    FAILED+=("AWS CLI")
  fi

  # Google Cloud SDK
  if [ "$HAS_BREW" -eq 1 ]; then
    attempt "Google Cloud SDK" "gcloud" "gcloud init" "brew install --cask google-cloud-sdk"
  elif [ "$HAS_CURL" -eq 1 ]; then
    attempt "Google Cloud SDK" "gcloud" "gcloud init" "curl -sSL https://sdk.cloud.google.com | bash"
  else
    warn "Google Cloud SDK skipped — see https://cloud.google.com/sdk/docs/install"
    FAILED+=("Google Cloud SDK")
  fi

  # Azure CLI
  if [ "$HAS_BREW" -eq 1 ]; then
    attempt "Azure CLI" "az" "az login" "brew install azure-cli"
  elif [ "$OS" = "linux" ] && [ "$HAS_CURL" -eq 1 ]; then
    attempt "Azure CLI" "az" "az login" "curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
  else
    warn "Azure CLI skipped — see https://learn.microsoft.com/cli/azure/install-azure-cli"
    FAILED+=("Azure CLI")
  fi

  # Oracle Cloud (OCI)
  if [ "$HAS_CURL" -eq 1 ]; then
    attempt "Oracle Cloud (oci)" "oci" "oci setup config" \
      "bash -c \"\$(curl -sL https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)\" -- --accept-all-defaults"
  else
    warn "OCI CLI skipped — see https://docs.oracle.com/iaas/Content/API/SDKDocs/cliinstall.htm"
    FAILED+=("OCI CLI")
  fi

  # IBM Cloud
  if [ "$HAS_CURL" -eq 1 ]; then
    attempt "IBM Cloud" "ibmcloud" "ibmcloud login" "curl -fsSL https://clis.cloud.ibm.com/install/linux | sh"
  else
    warn "IBM Cloud CLI skipped — see https://cloud.ibm.com/docs/cli"
    FAILED+=("IBM Cloud")
  fi
fi
echo

# =============================================================================
# Summary
# =============================================================================
info "${BOLD}Summary${RESET}"
printf '  %sInstalled (%d):%s %s\n'  "$GREEN" "${#INSTALLED[@]}" "$RESET" "${INSTALLED[*]:-none}"
printf '  %sAlready had (%d):%s %s\n' "$DIM"   "${#SKIPPED[@]}"   "$RESET" "${SKIPPED[*]:-none}"
printf '  %sFailed/skipped (%d):%s %s\n' "$RED" "${#FAILED[@]}"   "$RESET" "${FAILED[*]:-none}"
echo

if [ "$LIST_ONLY" -eq 1 ]; then
  exit 0
fi

info "${BOLD}Next step: log in to each tool you'll use${RESET} ${DIM}(installing did NOT create accounts)${RESET}"
if [ "${#LOGIN_HINTS[@]}" -eq 0 ]; then
  printf '  (nothing installed)\n'
else
  for hint in "${LOGIN_HINTS[@]}"; do
    name="${hint%%|*}"; cmd="${hint#*|}"
    printf '  %-26s %s%s%s\n' "$name" "$BOLD" "$cmd" "$RESET"
  done
fi
echo
printf '%s\n' "${DIM}You still need a (free) account on each provider's website before these logins work.${RESET}"
