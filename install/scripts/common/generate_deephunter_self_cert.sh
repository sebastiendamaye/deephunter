#!/bin/bash

# Variables
CERT_DIR="/data/cert"
PRIVATE_DIR="$CERT_DIR/private"
DOMAIN="deephunter.mydomain.com"
CERT_FILE="$CERT_DIR/deephunter.cer"
KEY_FILE="$PRIVATE_DIR/deephunter.key"

# Create directories if they don't exist
mkdir -p $CERT_DIR
mkdir -p $PRIVATE_DIR

# Generate the private key
openssl genpkey -algorithm RSA -out $KEY_FILE

# Generate the certificate signing request (CSR)
openssl req -new -key $KEY_FILE -out "$CERT_DIR/deephunter.csr" -subj "/CN=$DOMAIN"

# Generate the self-signed certificate
openssl x509 -req -days 365 -in "$CERT_DIR/deephunter.csr" -signkey $KEY_FILE -out $CERT_FILE

# Clean up the CSR file as it's no longer needed
rm "$CERT_DIR/deephunter.csr"

echo "Self-signed certificate and key have been generated:"
echo "Certificate: $CERT_FILE"
echo "Key: $KEY_FILE"
