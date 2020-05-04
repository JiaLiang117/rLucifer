pipeline {
    agent { docker { image 'python' } }
    stages {
        stage('build') {
            steps {
                sh 'python --version'
                sh 'python hello_world.py'
            }
        }
    }
}