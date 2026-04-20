#!/bin/bash
set -ex

# Use Garden's provided namespace if available, otherwise fallback to the PR pattern
NS="${GARDEN_NAMESPACE:-angry-agent-pr-${PR_NUMBER:-local}}"

echo "Using namespace: $NS"

POD_NAME="robot-test-runner"

# Ensure kubectl is in the path (standard on mac with homebrew)
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Wait for the pod to be ready
kubectl wait --for=condition=Ready pod/$POD_NAME -n $NS --timeout=120s

# Create target directory and copy tests
kubectl exec $POD_NAME -n $NS -- mkdir -p /tmp/robot-tests /tmp/reports
kubectl cp ./tests $POD_NAME:/tmp/robot-tests -n $NS

# Execute tests using the virtual environment's robot
# We cd to /tmp to avoid permission issues in the root directory
kubectl exec $POD_NAME -n $NS -- /bin/bash -c "
  export PATH=/home/pwuser/.venv/bin:\$PATH
  export HOME=/home/pwuser
  cd /tmp
  if ! robot --loglevel DEBUG -d /tmp/reports /tmp/robot-tests; then
    echo 'Tests failed, showing console log:'
    # Optional: robot usually outputs to console, but just in case we can't see it all
    exit 1
  fi
"
