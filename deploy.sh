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
    if [[ $(aws ecs update-service --cluster sample-webapp-cluster --service sample-webapp-service --task-definition $revision | \
                   $JQ '.service.taskDefinition') != $revision ]]; then
        echo "Error updating service."
        return 1
    fi

    # wait for older revisions to disappear
    # not really necessary, but nice for demos
    for attempt in {1..30}; do
        if stale=$(aws ecs describe-services --cluster sample-webapp-cluster --services sample-webapp-service | \
                       $JQ ".services[0].deployments | .[] | select(.taskDefinition != \"$revision\") | .taskDefinition"); then
            echo "Waiting for stale deployments:"
            echo "$stale"
            sleep 5
        else
            echo "Deployed!"
            return 0
        fi
    done
    echo "Service update took too long."
    return 1
}

make_task_def(){
	task_template='[
		{
			"name": "go-sample-webapp",
			"image": "%s.dkr.ecr.us-east-1.amazonaws.com/go-sample-webapp:%s",
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
	
	task_def=$(printf "$task_template" $AWS_ACCOUNT_ID $CIRCLE_SHA1)
}

push_ecr_image(){
	eval $(aws ecr get-login --region us-east-1)
	docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/go-sample-webapp:$CIRCLE_SHA1
}

push_dockerhub_image(){
  echo "Running push_dockerhub_image Started"
  # docker login --no-include-email -u $DOCKER_USERNAME -p $DOCKER_PASSWORD
	# docker push vinod/py-ecs:$CIRCLE_SHA1
	# docker push vinod/py-ecs
	eval $(aws ecr get-login --no-include-email --region us-west-2)
  echo "Login Completed"
  docker tag vinod/py-ecs:latest $AWS_ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/vinod/py-ecs:latest
  echo "Image Tagging Completed"
	# docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/go-sample-webapp:$CIRCLE_SHA1
  docker push $AWS_ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/vinod/py-ecs:latest
  echo "Pushing image completed"
  echo "Running push_dockerhub_image End"
}

push_dockerhub_image2(){
  echo "Running push_dockerhub_image Started"
  # docker login --no-include-email -u $DOCKER_USERNAME -p $DOCKER_PASSWORD
	# docker push vinod/py-ecs:$CIRCLE_SHA1
	# docker push vinod/py-ecs
	eval $(aws ecr get-login --no-include-email --region us-west-2)
  echo "Login Completed"
  docker tag vinod/py-ecs:latest $AWS_ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/vinod/py-ecs:latest
  echo "Image Tagging Completed"
	# docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/go-sample-webapp:$CIRCLE_SHA1
  docker push $AWS_ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/vinod/py-ecs:latest
  echo "Pushing image completed"
  echo "Running push_dockerhub_image End"
}

register_definition() {

    if revision=$(aws ecs register-task-definition --container-definitions "$task_def" --family $family | $JQ '.taskDefinition.taskDefinitionArn'); then
        echo "Revision: $revision"
    else
        echo "Failed to register task definition"
        return 1
    fi

}

configure_aws_cli
push_dockerhub_image
# deploy_cluster
