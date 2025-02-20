# Deplolyments
We use AWS CodePipeline to deploy the spider application as does the rest of the search application.  To deploy in AWS see the documents under CodePipeline.  Toward the pivot to Jemison we investigated if we could continue using this spider application in Cloud.gov.  As part of that investigation we added the capability to deploy to cloud.gov.

## Codedeploy
The [appspec.yml](../appspec.yml) file controls the actions taken on deployment.  We have customized this behavior with various [scripts](../cicd-scripts/) that control what happens on the host during each deploy.


## Cloud.gov
Our ability to deploye to cloud.gov is driven by the [manifest file](../manifest.yml) as well as a few other files in the root directory.
