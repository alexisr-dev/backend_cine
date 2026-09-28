#!/bin/sh
set -e

echo "Esperando a PostgreSQL en ${DB_HOST}:${DB_PORT}"
until python -c "import socket,os,sys; s=socket.socket(); s.settimeout(2); sys.exit(s.connect_ex((os.environ.get('DB_HOST','db'), int(os.environ.get('DB_PORT','5432')))))" 2>/dev/null; do
  sleep 1
done

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
