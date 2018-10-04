export MODEL_URL=https://github.com/ffais/cloud-asr/blob/master/resources/model.zip?raw=true

docker build -t smartcommunitylab/cloud-asr-base:test cloudasr/shared
docker build -t smartcommunitylab/cloud-asr-web:test cloudasr/web
docker build -t smartcommunitylab/cloud-asr-api:test cloudasr/api/
docker build -t smartcommunitylab/cloud-asr-worker:test --build-arg MODEL_URL="${MODEL_URL}" cloudasr/worker/
docker build -t smartcommunitylab/cloud-asr-master:test cloudasr/master/
docker build -t smartcommunitylab/cloud-asr-monitor:test cloudasr/monitor/
docker build -t smartcommunitylab/cloud-asr-recordings:test cloudasr/recordings/
