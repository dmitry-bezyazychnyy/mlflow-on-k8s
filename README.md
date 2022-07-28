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