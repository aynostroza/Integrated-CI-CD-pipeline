pipeline {
    // Apply the linux-python label to your existing Linux Jenkins container/node.
    agent { label 'linux-python' }

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 10, unit: 'MINUTES')
        timestamps()
    }

    triggers {
        githubPush()
    }

    environment {
        PYTHONUNBUFFERED = '1'
    }

    stages {
        stage('Checkout') {
            steps {
                deleteDir()
                script {
                    def revision = checkout scm
                    env.GIT_COMMIT = revision.GIT_COMMIT
                    env.GIT_BRANCH = revision.GIT_BRANCH
                }
                sh 'git log -1 --format="Commit: %H%nCommit time: %cI%nSubject: %s"'
            }
        }

        stage('Build') {
            steps {
                sh 'python3 --version'
                sh 'bash ci_lab/build.sh'
            }
        }

        stage('Unit tests') {
            steps {
                sh 'bash ci_lab/test.sh'
            }
        }

        stage('Archive artifact') {
            steps {
                archiveArtifacts artifacts: 'ci_lab/dist/calculator.pyz', fingerprint: true
            }
        }
    }

    post {
        always {
            script {
                // Snapshot the build/test result before attempting delivery.
                def result = currentBuild.currentResult
                if (fileExists('ci_lab/webex_notify.py')) {
                    // Delivery failures make a successful run UNSTABLE; a failed
                    // build remains FAILURE. Tokens are scoped to this step.
                    catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE', catchInterruptions: false) {
                        withCredentials([
                            string(credentialsId: 'webex-bot-token', variable: 'WEBEX_BOT_TOKEN'),
                            string(credentialsId: 'webex-room-id', variable: 'WEBEX_ROOM_ID')
                        ]) {
                            withEnv(["PIPELINE_RESULT=${result}"]) {
                                sh '''
                                    set +x
                                    python3 ci_lab/webex_notify.py notify --status "$PIPELINE_RESULT"
                                '''
                            }
                        }
                    }
                } else {
                    echo 'Webex notification unavailable: checkout did not provide ci_lab/webex_notify.py.'
                }
            }
        }
    }
}
