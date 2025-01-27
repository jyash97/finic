from database import Database
from models import AppConfig, Agent
import os
import zipfile
from google.cloud.devtools import cloudbuild_v1
from google.oauth2 import service_account
import json
from datetime import timedelta
from google.cloud import run_v2


class Deployer:
    def __init__(self):
        service_account_string = os.getenv("GCLOUD_SERVICE_ACCOUNT")
        self.deployments_bucket = os.getenv("DEPLOYMENTS_BUCKET")
        self.project_id = os.getenv("GCLOUD_PROJECT")
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(service_account_string)
        )

        self.build_client = cloudbuild_v1.CloudBuildClient(credentials=credentials)
        self.jobs_client = run_v2.JobsClient(credentials=credentials)

    def deploy_agent(self, agent: Agent):
        # Check if the job already exists in Cloud Run
        try:
            self.jobs_client.get_job(
                name=f"projects/{self.project_id}/locations/us-central1/jobs/{Agent.get_cloud_job_id(agent)}"
            )
            job_exists = True
        except Exception:
            job_exists = False

        # Define the build steps
        build_config = self._get_build_config(agent=agent, job_exists=job_exists)

        # Trigger the build
        build = cloudbuild_v1.Build(
            steps=build_config["steps"],
            images=build_config["images"],
            source=cloudbuild_v1.Source(
                storage_source=cloudbuild_v1.StorageSource(
                    bucket=self.deployments_bucket,
                    object_=f"{agent.finic_id}.zip",
                )
            ),
        )
        operation = self.build_client.create_build(
            project_id=self.project_id, build=build
        )

        # Wait for the build to complete
        result = operation.result()
        if result.status != cloudbuild_v1.Build.Status.SUCCESS:
            raise Exception(f"Build failed with status: {result.status}")

        print(f"Built and pushed Docker image: {agent.finic_id}")

    def _get_build_config(self, agent: Agent, job_exists: bool) -> dict:
        image_name = f"gcr.io/{self.project_id}/{agent.finic_id}:latest"
        gcs_source = f"gs://{self.deployments_bucket}/{agent.finic_id}.zip"
        job_command = "update" if job_exists else "create"
        return {
            "steps": [
                {
                    "name": "gcr.io/cloud-builders/gsutil",
                    "args": ["cp", gcs_source, "/workspace/source.zip"],
                },
                {
                    "name": "gcr.io/cloud-builders/gcloud",
                    "entrypoint": "bash",
                    "args": [
                        "-c",
                        "apt-get update && apt-get install -y unzip && unzip /workspace/source.zip -d /workspace/unzipped",
                    ],
                },
                {
                    "name": "gcr.io/cloud-builders/docker",
                    "args": ["build", "-t", image_name, "/workspace/unzipped"],
                },
                {
                    "name": "gcr.io/cloud-builders/docker",
                    "args": ["push", image_name],
                },
                {
                    "name": "gcr.io/google.com/cloudsdktool/cloud-sdk",
                    "entrypoint": "bash",
                    "args": [
                        "-c",
                        f"gcloud run jobs {job_command} {Agent.get_cloud_job_id(agent)} --image {image_name} --region us-central1 "
                        f"--tasks=1 --max-retries={agent.num_retries} --task-timeout=86400s --memory=4Gi",
                    ],
                },
            ],
            "images": [image_name],
        }
