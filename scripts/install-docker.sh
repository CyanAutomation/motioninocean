#!/usr/bin/env bash

set -e

if command -v docker &> /dev/null; then
    echo "Docker is already installed. Exiting."
    exit 0
fi


echo "Attempting to remove old Docker packages if they exist..."
for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do
    # Using -qq to suppress output and -y for non-interactive removal.
    # Check if the package is installed before attempting to remove it to avoid unnecessary error messages.
    if dpkg -s $pkg &> /dev/null; then
        if sudo apt-get remove -qq -y $pkg; then
            echo "Successfully removed $pkg."
        else
            echo "Warning: Could not remove $pkg."
            # Do not exit here, continue with other packages
        fi
    else
        echo "$pkg not installed, skipping removal."
    fi
done

echo "Downloading Docker installation script..."
if curl -fsSL https://get.docker.com -o get-docker.sh; then
    echo "Docker installation script downloaded successfully."
else
    echo "Error: Failed to download Docker installation script."
    exit 1
fi

echo "Running Docker installation script..."
if sudo sh ./get-docker.sh; then
    echo "Docker installed successfully."
else
    echo "Error: Docker installation failed."
    rm -f get-docker.sh # Clean up downloaded script on failure
    exit 1
fi

# verify
echo "Verifying Docker installation..."
if sudo docker run hello-world; then
    echo "Docker installation verified with 'hello-world'."
else
    exit 1
fi

rm -f get-docker.sh # Clean up the downloaded script

echo "Adding current user to the 'docker' group to run Docker without sudo..."
sudo usermod -aG docker "${USER}"
echo "Please log out and log back in for the group change to take effect."
