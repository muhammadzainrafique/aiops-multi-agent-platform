{ pkgs ? import <nixpkgs> {} }:

let
  # Switch to python312 to satisfy the Sphinx 9.x requirement
  pythonEnv = pkgs.python312.withPackages (ps: with ps; [
    flask
    redis
    kubernetes
    python-dotenv
    pytest
    pip 
  ]);
in
pkgs.mkShell {
  buildInputs = [
    pythonEnv
    pkgs.redis
    pkgs.kubectl
  ];

  shellHook = ''
    if [ ! -f .env ]; then
      cp .env.example .env
      echo ".env created from .example"
    fi

    # Ensure pip installs into a local directory to avoid store conflicts
    export PIP_PREFIX="$(pwd)/.nix-pip"
    export PYTHONPATH="$PIP_PREFIX/${pkgs.python312.sitePackages}:$PYTHONPATH"
    export PATH="$PIP_PREFIX/bin:$PATH"
    
    unset SOURCE_DATE_EPOCH
    pip install groq --quiet


    # 3. Start Redis in the background
    echo "Starting Redis server..."
    # Launch redis and redirect logs to a temp file so it doesn't clutter your terminal
    redis-server --port 6379 --daemonize yes --logfile .redis.log

    echo "AI-Ops Environment Ready (Python 3.12)"
    echo "Run: PYTHONPATH=. python agents/supervisor/main.py"
  '';
}