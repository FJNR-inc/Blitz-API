pipeline {
  agent {
    docker {
        image 'docker:20.10.24-cli-alpine3.18'
        args '-v /var/run/docker.sock:/var/run/docker.sock'
    }
  }
  environment {
    HOME = '.'
  }
  stages {
    stage('Debug info') {
      steps {
        sh 'docker compose --version'
      }
    }
    stage('Build images') {
      steps {
        sh 'docker compose build'
      }
    }
    stage('Static code analysis') {
      steps {
        sh 'docker compose run --rm api pycodestyle --config=.pycodestylerc .'
      }
    }
    stage('Unit tests') {
      steps {
        sh 'docker compose run --rm api python manage.py test'
      }
    }
    stage('deploy QA') {
      when{
        expression {
          return env.BRANCH_NAME == 'develop';
        }
      }
      steps {
        sh '''
        # No deploy QA
        '''
      }
    }
    stage('Store official image') {
      when{
        expression {
          return env.BRANCH_NAME == 'master';
        }
      }
      steps {
        sh '''
        # No image repository
        '''
      }
    }
    stage("Final Cleanup") {
      steps {
        cleanWs deleteDirs: true, notFailBuild: true
      }
    }
  }
}
