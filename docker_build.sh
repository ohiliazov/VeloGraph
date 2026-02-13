VERSION="${1}"

docker build -t "ohiliazov/velograph-api:${VERSION}" --platform=linux/arm64,linux/amd64 --push backend &
docker build -t "ohiliazov/velograph-web:${VERSION}" --platform=linux/arm64,linux/amd64 --push frontend &

wait
