import boto3
import logging
import sys

logger = logging.getLogger('thestral_aws_lambda')
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


def submit_job(batch_client, job_definition_name, job_name, job_queue_name):
    response = batch_client.submit_job(
        jobDefinition=job_definition_name,
        jobName=job_name,
        jobQueue=job_queue_name,
    )
    logger.info("Submit job response %s", response)


def lambda_handler(event, context):
    logger.info("submit_job Started")
    batch_client = boto3.client('batch')
    job_queue_name = 'thestral_job_queue'
    job_definition_name = 'thestral_job_definition'
    job_name = 'thestral_job'
    submit_job(batch_client, job_definition_name, job_name, job_queue_name)
    logger.info("submit_job Completed")
