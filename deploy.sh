#!/usr/bin/env bash

# more bash-friendly output for jq
JQ="jq --raw-output --exit-status"

configure_aws_cli(){
	aws --version
	aws configure set default.region us-west-2
	aws configure set default.output json
}

deploy_cluster() {

    family="sample-webapp-task-family"

    make_task_def
    register_definition
    # if [[ $(aws ecs update-service --cluster sample-webapp-cluster --service sample-webapp-service --task-definition $revision | \
    #                $JQ '.service.taskDefinition') != $revision ]]; then
    #     echo "Error updating service."
    #     return 1
    # fi
    #
    # # wait for older revisions to disappear
    # # not really necessary, but nice for demos
    # for attempt in {1..30}; do
    #     if stale=$(aws ecs describe-services --cluster sample-webapp-cluster --services sample-webapp-service | \
    #                    $JQ ".services[0].deployments | .[] | select(.taskDefinition != \"$revision\") | .taskDefinition"); then
    #         echo "Waiting for stale deployments:"
    #         echo "$stale"
    #         sleep 5
    #     else
    #         echo "Deployed!"
    #         return 0
    #     fi
    # done
    # echo "Service update took too long."
    # return 1
}

make_task_def(){
	task_template='[
		{
			"name": "go-sample-webapp",
			"image": "vinodsharma/circleci-demo-docker:459049b9305ed6d5b74f62fe5c06c7620b5e7214",
			"essential": true,
			"memory": 200,
			"cpu": 10,
			"portMappings": [
				{
					"containerPort": 8080,
					"hostPort": 80
				}
			]
		}
	]'
	
	# task_def=$(printf "$task_template" $DOCKERHUB_REPO_NAME $CIRCLE_SHA1)
	task_def=$(printf "$task_template")
  echo $task_def
}

register_definition() {

    if revision=$(aws ecs register-task-definition --container-definitions "$task_def" --family $family | $JQ '.taskDefinition.taskDefinitionArn'); then
        echo "Revision: $revision"
    else
        echo "Failed to register task definition"
        return 1
    fi

}

DOCKERHUB_REPO_NAME="vinodsharma/circleci-demo-docker"
push_dockerhub_image(){
  echo "Running push_dockerhub_image Started"
  docker login -u $DOCKER_USERNAME -p $DOCKER_PASSWORD
  echo "Login Completed"
  # docker push vinodsharma/circleci-demo-docker:$CIRCLE_SHA1
  docker push $DOCKERHUB_REPO_NAME:$CIRCLE_SHA1
  echo "Pushing image to dockerhub completed"
  echo "Running push_dockerhub_image Ended"
}

setup_cloudwatch(){
  # aws events put-rule --name my-scheduled-rule --schedule-expression 'rate(1 minute)'
  aws events put-rule --name my-scheduled-rule --schedule-expression 'rate(1 minute)' | jq -r '.RuleArn'
}


configure_aws_cli
# push_dockerhub_image
setup_cloudwatch
deploy_cluster
