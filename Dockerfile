# ---- Builder stage ----
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy only what's needed for the build
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

# Create venv and install all extras
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir '.[all]'

# Install Playwright Chromium browser
RUN playwright install chromium

# ---- Runtime stage ----
FROM python:3.12-slim

# Runtime system deps: tesseract for OCR, curl for healthcheck,
# shared libs required by Playwright Chromium, and Node.js for Claude Code
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    curl \
    # Playwright Chromium shared libs
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libxshmfence1 \
    libx11-xcb1 \
    fonts-liberation \
    # Node.js dependencies for Claude Code
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x (required for Claude Code)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy Playwright browsers from builder
COPY --from=builder /root/.cache/ms-playwright /home/pocketpaw/.cache/ms-playwright

# Create non-root user
RUN groupadd --system pocketpaw && \
    useradd --system --gid pocketpaw --create-home pocketpaw && \
    mkdir -p /home/pocketpaw/.pocketpaw && \
    chown -R pocketpaw:pocketpaw /home/pocketpaw

# Install Claude Code globally as root (npm global install needs root)
RUN npm install -g @anthropic-ai/claude-code --registry=https://registry.npmmirror.com

# Configure Claude Code to skip onboarding (create config for pocketpaw user)
RUN mkdir -p /home/pocketpaw/.config && \
    echo '{"hasCompletedOnboarding": true, "preferredNotToShare": true}' > /home/pocketpaw/.claude.json && \
    chown -R pocketpaw:pocketpaw /home/pocketpaw/.claude.json

# Run as root for full shell access
USER root
WORKDIR /home/pocketpaw

# PocketPaw web configuration
ENV POCKETPAW_WEB_HOST=0.0.0.0
ENV POCKETPAW_WEB_PORT=8888
ENV POCKETPAW_LOCALHOST_AUTH_BYPASS=false

# Kimi Code API Configuration (Claude Code will use these)
ENV ANTHROPIC_BASE_URL=https://api.kimi.com/coding/
# ANTHROPIC_API_KEY should be set at runtime via Railway/dashboard

# Claude Code configuration for PocketPaw
ENV POCKETPAW_CLAUDE_CODE_ENABLED=true
ENV POCKETPAW_CLAUDE_CODE_PATH=/usr/local/bin/claude

EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8888/ || exit 1
    
CMD ["pocketpaw"]
