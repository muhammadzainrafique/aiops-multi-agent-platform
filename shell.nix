{ pkgs ? import <nixpkgs> {} }:
let
  pythonEnv = pkgs.python312.withPackages (ps: with ps; [
    flask
    redis
    kubernetes
    python-dotenv
    pytest
    pip
  ]);
in pkgs.mkShell {
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

    export PIP_PREFIX="$(pwd)/.nix-pip"
    export PYTHONPATH="$PIP_PREFIX/${pkgs.python312.sitePackages}:$PYTHONPATH"
    export PATH="$PIP_PREFIX/bin:$PATH"

    unset SOURCE_DATE_EPOCH
    pip install groq --quiet
    pip install "discord.py>=2.3.0" requests --quiet

    echo "Starting Redis server..."
    redis-server --port 6379 --daemonize yes --logfile .redis.log

    echo "AI-Ops Environment Ready (Python 3.12)"
    echo "Run: PYTHONPATH=. python agents/supervisor/main.py"
  '';
}