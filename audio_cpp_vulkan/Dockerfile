# syntax=docker/dockerfile:1
# Audio.cpp - local audio inference server for Home Assistant
# Upstream: https://github.com/0xShug0/audio.cpp (Apache-2.0)
# renovate: datasource=docker depName=ubuntu
ARG UBUNTU_VERSION=26.04
# renovate: datasource=docker depName=ghcr.io/home-assistant/base-ubuntu
ARG BASE_UBUNTU_VERSION=24.04
# renovate: datasource=github-releases depName=0xShug0/audio.cpp versioning=semver extractVersion=^v(?<version>.+)$
ARG AUDIOCPP_VERSION=0.9.3
ARG AUDIOCPP_MODELS=citrinet_asr,qwen3_asr,canary_asr,sense_asr,moonshine_asr,parakeet_tdt,whistle_asr,niagara_asr,granite5asr,hviske_asr,hviske_asr_v6,owsm,nemotron_asr,kroko_asr,fun_asr_nano,pocket_tts
# renovate: datasource=github-tags depName=m-abs/wyoming_audiocpp versioning=loose
ARG WYO_VERSION=0.2.1-rc2

FROM ubuntu:${UBUNTU_VERSION} AS build
ARG AUDIOCPP_VERSION
ARG AUDIOCPP_MODELS
ARG WYO_VERSION
ENV DEBIAN_FRONTEND=noninteractive
ENV CC=gcc-14 \
    CXX=g++-14
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        cmake \
        curl \
        g++-14 \
        gcc-14 \
        glslc \
        libgomp1 \
        libssl-dev \
        libvulkan-dev \
        make \
        spirv-headers \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN curl -fsSL "https://github.com/0xShug0/audio.cpp/archive/refs/tags/v${AUDIOCPP_VERSION}.tar.gz" \
        | tar xz --strip-components=1
RUN mkdir -p /src/wyoming \
    && curl -fsSL "https://github.com/m-abs/wyoming_audiocpp/archive/refs/tags/${WYO_VERSION}.tar.gz" \
        | tar xz --strip-components=1 -C /src/wyoming \
    && test -d /src/wyoming/wyoming_audiocpp_common \
    && test -d /src/wyoming/wyoming_audiocpp_asr \
    && test -d /src/wyoming/wyoming_audiocpp_tts \
    && test -f /src/wyoming/wyoming_audiocpp_tts/params.json
RUN cmake -S . -B build \
        -DCMAKE_BUILD_TYPE=Release \
        -DAUDIOCPP_VERSION="${AUDIOCPP_VERSION}" \
        -DAUDIOCPP_MODEL_SET=custom \
        -DAUDIOCPP_MODELS="${AUDIOCPP_MODELS}" \
        -DENGINE_ENABLE_CUDA=OFF \
        -DENGINE_ENABLE_VULKAN=ON \
        -DENGINE_ENABLE_OPENMP=ON \
        -DENGINE_ENABLE_NATIVE_CPU=OFF \
        -DENGINE_ENABLE_CPU_ALL_VARIANTS=ON \
        -DAUDIOCPP_BUILD_NATIVE_MODEL_MANAGER=ON \
        -DAUDIOCPP_USE_SYSTEM_OPENSSL=ON \
        -DAUDIOCPP_DEPLOYMENT_BUILD=ON \
        -DENGINE_BUILD_EXAMPLES=OFF \
        -DENGINE_BUILD_TESTS=OFF \
        -DENGINE_BUILD_WARMBENCH=OFF \
    && cmake --build build --parallel "$(nproc)" \
        --target audiocpp_server \
        --target audiocpp_model_manager
# Runtime shared libraries (per-ISA ggml CPU backends) must sit next to the binary
RUN mkdir -p /app && find build -name "*.so*" -exec cp -P {} /app/ \;

FROM ghcr.io/home-assistant/base-ubuntu:${BASE_UBUNTU_VERSION}
ARG AUDIOCPP_VERSION
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH="/app/wyoming" \
    PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libegl1 \
        libgl1 \
        libgomp1 \
        libgles2 \
        libglvnd0 \
        libglx0 \
        libssl3 \
        libstdc++6 \
        libvulkan1 \
        mesa-vulkan-drivers \
        python3 \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/wyoming \
    && /opt/wyoming/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/wyoming/bin/pip install --no-cache-dir "wyoming>=1.10.2,<2" "requests>=2.31,<3"
COPY --from=build /src/build/bin/audiocpp_server /app/audiocpp_server
COPY --from=build /src/build/bin/audiocpp_model_manager /app/audiocpp_model_manager
COPY --from=build /app/ /app/
COPY --from=build /src/model_specs/ /app/model_specs/
COPY --from=build /src/wyoming/wyoming_audiocpp_common /app/wyoming/wyoming_audiocpp_common
COPY --from=build /src/wyoming/wyoming_audiocpp_asr /app/wyoming/wyoming_audiocpp_asr
COPY --from=build /src/wyoming/wyoming_audiocpp_tts /app/wyoming/wyoming_audiocpp_tts
# Copy root filesystem. The Supervisor does not do this, the image has to
# bring the s6 services with it.
COPY rootfs /
WORKDIR /app
LABEL \
    org.opencontainers.image.title="Home Assistant App: Audio.cpp Vulkan" \
    org.opencontainers.image.description="Local speech-to-text server based on audio.cpp, with the Vulkan GPU backend." \
    org.opencontainers.image.source="https://github.com/pollonamid/ha-apps" \
    org.opencontainers.image.licenses="Apache-2.0"
EXPOSE 8099 11301 11201
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=12 \
    CMD curl -fsS http://127.0.0.1:8099/health || exit 1
