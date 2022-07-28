docker-build-prj:
	docker build -t dmitryb/wine-quality:base -f ./Dockerfiles/Dockerfile.project .
	docker push dmitryb/wine-quality:base

docker-build-mlflow:
	docker build -t dmitryb/mlflow:1.20.0-arm -f ./Dockerfiles/Dockerfile.mlflow .
	docker push dmitryb/mlflow:1.20.0-arm

create-k8s-local:
	k3d cluster create --api-port 6550 -p "8081:80@loadbalancer" --agents 2

create-k8s-ns:
	kubectl create ns mlflow
	kubectl create ns minio

deploy-all: deploy-postgres deploy-minio deploy-mlflow
	echo "."

deploy-postgres:
	kubectl apply -f k8s/postgres.yaml

deploy-minio:
	kubectl apply -f k8s/minio.yaml

deploy-mlflow:
	kubectl apply -f k8s/mlflow.yaml