#!/bin/bash
# server/generate_cert.sh

echo "================================================"
echo "SSL CERTIFICATE GENERATION FOR JOB QUEUE SERVER"
echo "================================================"

# Get server IP or hostname
echo ""
echo "Enter server hostname or IP address:"
read -p "(default: 100.89.185.61): " SERVER_ADDRESS
SERVER_ADDRESS=${SERVER_ADDRESS:-100.89.185.61}

echo ""
echo "Generating SSL certificate for: $SERVER_ADDRESS"
echo ""

# Generate private key and certificate in one command
openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout key.pem \
    -out cert.pem \
    -days 365 \
    -subj "/C=IN/ST=Karnataka/L=Bengaluru/O=JobQueue/OU=Distributed Systems/CN=$SERVER_ADDRESS" \
    -addext "subjectAltName=IP:$SERVER_ADDRESS"

echo ""
echo "================================================"
echo "CERTIFICATE GENERATED SUCCESSFULLY!"
echo "================================================"
echo "Files created:"
echo "  - cert.pem (Certificate)"
echo "  - key.pem (Private Key)"
echo ""
echo "Certificate details:"
openssl x509 -in cert.pem -noout -subject -dates
echo ""
echo "Common Name (CN): $SERVER_ADDRESS"
echo "Valid for: 365 days"
echo ""
echo "================================================"
echo "NEXT STEPS:"
echo "1. Keep key.pem PRIVATE and secure"
echo "2. Copy cert.pem to worker and client machines"
echo "3. Run server with these certificates"
echo "================================================"
