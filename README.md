# mlflow-on-k8s
This project shows how to deploy MlFlow on k8s (local) and train simple model that predicts wine quality. We will be using Minio (s3 compatible storage) for storing all artifacts.

## Create local k8s (skip if you have k8s)
We're assuming you don't have k8s, so let's create a local. You also need to install docker.

First, lets install [k3d](https://k3d.io/v5.4.4/) by running:

`brew install k3d`

Let's create a k8s instance with 2 nodes and ingress service bound to local port 8081:

`k3d cluster create --api-port 6550 -p "8081:80@loadbalancer" --agents 2`

When it's done, it will create (append to) a config file in `~/.kube/config`

Install kubectl: 

`brew install kubectl`

Verify that cluster is ready by checking available nodes: 

`kubectl get nodes`

```sh
NAME                       STATUS   ROLES                  AGE   VERSION
k3d-k3s-default-server-0   Ready    control-plane,master   31h   v1.23.8+k3s1
k3d-k3s-default-agent-1    Ready    <none>                 31h   v1.23.8+k3s1
k3d-k3s-default-agent-0    Ready    <none>                 31h   v1.23.8+k3s1
```

## Deploy MlFlow on k8s

Deploy Postgres (data will be stored in persist volume):

`make deploy-postgres`

Deploy minio (s3 compatible storage). Likewise, the data will be stored in a persistent volume.

`make deploy-minio`

Finally, deploy mlflow:

`make deploy-mlflow`

Check that all containers are ready:

`kubectl get pod --all-namespaces`

You should be able to see something similar to:

```sh
NAMESPACE     NAME                                      READY   STATUS      RESTARTS   AGE
kube-system   local-path-provisioner-6c79684f77-ghrjt   1/1     Running     0          31h
kube-system   metrics-server-7cd5fcb6b7-qjcr8           1/1     Running     0          31h
kube-system   coredns-d76bd69b-8fc25                    1/1     Running     0          31h
kube-system   helm-install-traefik-crd-66jgr            0/1     Completed   0          31h
kube-system   helm-install-traefik-rkmt6                0/1     Completed   0          31h
kube-system   svclb-traefik-91f7cd6b-kqxwd              2/2     Running     0          31h
kube-system   svclb-traefik-91f7cd6b-5xhhr              2/2     Running     0          31h
kube-system   svclb-traefik-91f7cd6b-2d7k2              2/2     Running     0          31h
kube-system   traefik-df4ff85d6-qfz8c                   1/1     Running     0          31h
default       nginx-85b98978db-22qlh                    1/1     Running     0          17h
minio         minio-deployment-f964dc8d-6l8mt           1/1     Running     0          7h19m
mlflow        mlflow-postgres-0                         1/1     Running     0          7h10m
mlflow        mlflow-deployment-769f5865fd-96rfm        1/1     Running     0          7h3m
```

## Update hosts

Now we are going to create some names for easy access to mlflow and minio services. You would need to modify `/etc/hosts` by adding the following lines:

```sh
127.0.0.1 mlflow-service.mlflow
127.0.0.1 minio-service.minio
```

By now, you should be able to open minio and mlflow in your browser:

`open http://mlflow-service.mlflow:8081`
`open http://minio-service.minio:8081` (usr/pwd: minio123/minio123)

## Create a bucket for storing mlflow results

Mlflow has been deployed and configured to use the `/mlflow` bucket as the default location for storing artifacts. We will need to create this bucket manually using the minio UI.

## Set environments

To run the mlflow command and also access the minio bucket you need to install the following envs:

```bash
export MLFLOW_TRACKING_URI=http://mlflow-service.mlflow:8081
export MLFLOW_S3_ENDPOINT_URL=http://minio-service.minio:8081
export AWS_ACCESS_KEY_ID=minio123
export AWS_SECRET_ACCESS_KEY=minio123
```

## Train model and save results in mlflow

We would need to create a new conda environment.

`conda env create --file=./wine-quality-prj/conda.yaml`

Activate new env: `conda activate wine-quality-env`

`./wine-quality-prj` is a project example that trains wine prediction model. 
Use the following command to run it with mlflow:

```bash
mlflow run ./wine-quality-prj \
    --env-manager local \
    -e main \
    --experiment-name Default \
    --run-name run-1 \
    -P alpha=1.0
```

In console, you should be able to see something like:

```txt
2022/07/28 16:45:24 INFO mlflow.projects.utils: === Created directory /var/folders/6w/zxd0f8js0_b__bk2b3x_24nc0000gp/T/tmppvbqn5ka for downloading remote URIs passed to arguments of type 'path' ===
2022/07/28 16:45:24 INFO mlflow.projects.backend.local: === Running command 'python train.py 1.0 0.1' in run with ID '9c4b7bbb4251481eaa523d8db293de93' === 
INFO:root:
            RMSA: 0.8107373707184711
            MAE:  0.6241295925236753
            R2:   0.15105362812007328
        
INFO:botocore.credentials:Found credentials in environment variables.
Registered model 'ElasticNetModel_v1' already exists. Creating a new version of this model...
2022/07/28 16:45:32 INFO mlflow.tracking._model_registry.client: Waiting up to 300 seconds for model version to finish creation.                     Model name: ElasticNetModel_v1, version 3
Created version '3' of model 'ElasticNetModel_v1'.
INFO:root:model: ElasticNetModel_v1, version: 3
2022/07/28 16:45:32 INFO mlflow.projects: === Run (ID '9c4b7bbb4251481eaa523d8db293de93') succeeded ===
```

Now, if you go to mlflow (UI), you should be able to see a `run-1` in `Default` experiment with collected parameters, metrics and the output model (artifacts). Also, the model was registered in the model registry (as version x) and accessible via API and CLI.


MlFlow stores artifacts (models, etc) in S3 (minio in our case). You should be able to see them by running (Need to install awscli (`brew install awscli`)):

```bash
aws --endpoint-url http://minio-service.minio:8081 \
    s3 ls s3://mlflow
```

Results:

```txt
aws --endpoint-url http://minio-service.minio:8081 \
>     s3 ls s3://mlflow
                           PRE 0/
```

Where `0/` is a path for storing all runs + artiacts for experiment with id = 0 (Default)

## Running jobs on k8s 

We used to run a training job locally in a conda environment and publish metrics and artifacts (model) to mlflow. What if we want to do training on k8s too? There are many reasons to do this - more resources on a cluster (multiple GPU), can run multiple runs (training jobs) concurrently, good isolation (jobs are running inside containers), etc.
To do this, we need a few things: a docker image to use as a base, and a slight update to the Mlproject.

First, let's create a base docker image by running:

`make docker-build-prj`

This command builds a new image `dmitryb/wine-quality:base` with required dependencies and push to dockerhub (can use custom container registry).

Second, lets update the following lines in our MLproject:

```yaml
# use conda env
# conda_env: conda.yaml
# or
# use docker
docker_env: 
  image: dmitryb/wine-quality:base
```

Essentially, this means that we want to use the Docker image (which we just created) instead of the conda env.

Now, lets start the training job (with two more params `--backend` and `--backend-config`)

```bash
mlflow run ./wine-quality-prj \
    --backend kubernetes --backend-config wine-quality-prj/k8s_cfg.json \
    -e main \
    --experiment-name Default \
    --run-name run-1 \
    -P alpha=1.0
```

You will see something similar to:

```txt
2022/07/28 18:58:56 INFO mlflow.projects.docker: === Building docker image dmitryb/wine-quality:a5db207 ===
2022/07/28 18:58:57 INFO mlflow.projects.kubernetes: === Pushing docker image dmitryb/wine-quality:a5db207 ===
2022/07/28 18:59:05 INFO mlflow.projects.utils: === Created directory /var/folders/6w/zxd0f8js0_b__bk2b3x_24nc0000gp/T/tmpjp571h7k for downloading remote URIs passed to arguments of type 'path' ===
2022/07/28 18:59:05 INFO mlflow.projects.kubernetes: === Creating Job wine-quality-2022-07-28-18-59-05-832261 ===
2022/07/28 18:59:05 INFO mlflow.projects.kubernetes: Job started.
2022/07/28 18:59:15 INFO mlflow.projects.kubernetes: None
2022/07/28 18:59:15 INFO mlflow.projects: === Run (ID '7ea0b034da6a445786446ac4088eeff6') succeeded ===
```

This command does several things:
1. It creates a new image tagged a5db207 (current commit ID) using the base image.
2. push it to registry (docker hub in this example)
3. start k8s job using configuration and template we provided

If you go to mlflow UI, you should be able to see new run with all artifacts.

## Serve trained model

### Run webserver locally

```bash
# use run id (get if rom ui or using cli)
# Note: get correct run id from MLflow and replace <ace78a96b5af492cb27b0afeac7edd47>
mlflow models serve --env-manager=local --model-uri s3://mlflow/0/ace78a96b5af492cb27b0afeac7edd47/artifacts/model
# or use model name / version (or stage)
mlflow models serve --env-manager=local --model-uri models:/ElasticNetModel_v1/Staging
```

Expected result:

```bash
1/Staging
2022/07/29 16:37:45 INFO mlflow.models.cli: Selected backend for flavor 'python_function'
2022/07/29 16:37:45 INFO mlflow.pyfunc.backend: === Running command 'exec gunicorn --timeout=60 -b 127.0.0.1:5000 -w 1 ${GUNICORN_CMD_ARGS} -- mlflow.pyfunc.scoring_server.wsgi:app'
[2022-07-29 16:37:45 +0300] [66889] [INFO] Starting gunicorn 20.1.0
[2022-07-29 16:37:45 +0300] [66889] [INFO] Listening at: http://127.0.0.1:5000 (66889)
[2022-07-29 16:37:45 +0300] [66889] [INFO] Using worker: sync
[2022-07-29 16:37:45 +0300] [66890] [INFO] Booting worker with pid: 66890
^C[2022-07-29 16:37:47 +0300] [66889] [INFO] Handling signal: int
[2022-07-29 16:37:47 +0300] [66890] [INFO] Worker exiting (pid: 66890)
```

### Call model service

Using curl:

```bash
curl http://127.0.0.1:5000/invocations -H 'Content-Type: application/json' -d '{
    "columns": ["fixed acidity", "volatile acidity", "citric acid", "residual sugar", "chlorides", "free sulfur dioxide", "total sulfur dioxide", "density", "pH", "sulphates", "alcohol"],
    "data": [
        [6.30e+00, 3.00e-01, 3.40e-01, 1.60e+00, 4.90e-02, 1.40e+01, 1.32e+02, 9.94e-01, 3.30e+00, 4.90e-01, 9.50e+00],
        [6.10e+00, 3.00e-01, 3.40e-01, 1.60e+00, 1.90e-02, 1.40e+01, 4.32e+02, 9.94e-01, 3.30e+00, 4.90e-01, 9.50e+00]
    ]
}'
```

### Build docker image

Build docker image and run container (locally)

```bash
mlflow models build-docker \
    -m "models:/ElasticNetModel_v1/Production" \
    -n "dmitryb/wine-quality-prj"

docker run -p 5000:8080 --rm "dmitryb/wine-quality-prj"
```

Use the same curl request to make sure the model works.

### Load model as python function

```python
import mlflow.pyfunc
import pandas as pd

model_name = "ElasticNetModel_v1"
stage = 'Production' # or model version (get from mlflow)
model = mlflow.pyfunc.load_model(
    model_uri=f"models:/{model_name}/{stage}"
)

request = pd.DataFrame(
    data=[
        [6.30e+00, 3.00e-01, 3.40e-01, 1.60e+00, 4.90e-02, 1.40e+01, 1.32e+02, 9.94e-01, 3.30e+00, 4.90e-01, 9.50e+00],
        [6.10e+00, 3.00e-01, 3.40e-01, 1.60e+00, 1.90e-02, 1.40e+01, 4.32e+02, 9.94e-01, 3.30e+00, 4.90e-01, 9.50e+00]
    ],
    columns=["fixed acidity", "volatile acidity", "citric acid", "residual sugar", "chlorides", "free sulfur dioxide", "total sulfur dioxide", "density", "pH", "sulphates", "alcohol"]
)
response = model.predict(request)
print(response)
```