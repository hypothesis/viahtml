/**
 * This app's Jenkins Pipeline.
 *
 * This is written in Jenkins Scripted Pipeline language.
 * For docs see:
 * https://jenkins.io/doc/book/pipeline/syntax/#scripted-pipeline
*/

// Import the Hypothesis shared pipeline library, which is defined in this
// repo: https://github.com/hypothesis/pipeline-library
@Library("pipeline-library") _

// The the built hypothesis/viahtml Docker image.
def img

node {
    // The args that we'll pass to Docker run each time we run the Docker
    // image.
    runArgs = "-u root -e SITE_PACKAGES=true"

    stage("Build") {
        // Checkout the commit that triggered this pipeline run.
        checkout scm
        // Build the Docker image.
        img = buildApp(name: "hypothesis/viahtml")
    }

    stage("Tests") {
        testApp(image: img, runArgs: "${runArgs}") {
            installDeps()
            run("make test")
        }
    }

    onlyOnMain {
        stage("Release") {
            releaseApp(image: img)
        }
    }
}

onlyOnMain {
    milestone()
    stage("Deploy (qa)") {
	lock("qa deploy") {
	    parallel(
	        public: {
		    deployApp(image: img, app: "viahtml", env: "qa")
		},
		lms: {
		    // Workaround to ensure all parallel builds happen. See https://hypothes-is.slack.com/archives/CR3E3S7K8/p1625041642057400 
		    sleep 2
		    deployApp(image: img, app: "lms-viahtml", env: "qa")
		}
	    )
	}
    }

    milestone()
    stage("Approval") {
        input(message: "Proceed to production deploy?")
    }

    milestone()
    stage("Deploy (prod)") {
	lock("prod deploy") {
	    parallel(
	        public: {
		    deployApp(image: img, app: "viahtml", env: "prod")
		},
		lms: {
		    // Workaround to ensure all parallel builds happen. See https://hypothes-is.slack.com/archives/CR3E3S7K8/p1625041642057400 
		    sleep 2
		    deployApp(image: img, app: "lms-viahtml", env: "prod")
		}
	    )
	}
    }
}

/**
 * Install some common system dependencies.
 *
 * These are test dependencies that're need to run most of the stages above
 * (tests, lint, ...) but that aren't installed in the production Docker image.
 */
def installDeps() {
    sh "pip3 install -q tox>=3.8.0"
}

/** Run the given command. */
def run(command) {
    sh "apk add build-base"
    sh "cd /var/lib/hypothesis && ${command}"
}
