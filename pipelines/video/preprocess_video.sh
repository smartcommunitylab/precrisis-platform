#!/bin/bash

# Step 1: Rename file

# Check if exactly one argument (filename) is provided
if [ $# -ne 1 ]; then
  echo "Usage: $0 <filename>"
  exit 1
fi

# Get the filename from the argument
filename="$1"

# Function to remove special characters and lowercase the filename
sanitize_filename() { basename "${1}" | tr -d '[[:punct:] ]' | tr '[:upper:]' '[:lower:]'; }

# Get the cleaned filename
# filename="My File Name.with.special$char.txt"
sanitized_name=$(sanitize_filename "$filename")

mkdir tmp

# Check if the file exists
if [ ! -f "$filename" ]; then
  echo "Error: File '$filename' does not exist."
  exit 1
fi

# copy and replace name
cp "$filename" tmp/"$sanitized_name"

echo "File renamed to: $sanitized_name"

# Step 2: copy file to process folders

# Crowd Violence



