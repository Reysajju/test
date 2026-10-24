# Use official Playwright image with pre-installed Chromium & dependencies
FROM mcr.microsoft.com/playwright:v1.49.0-noble

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy application files
COPY . .

# Environment variables
ENV NODE_ENV=production

# Start the multi-zone scraper orchestrator
CMD ["node", "start_dental_scraper.js"]
