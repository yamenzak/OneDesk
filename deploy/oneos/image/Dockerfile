# syntax=docker/dockerfile:1

FROM lscr.io/linuxserver/baseimage-selkies:alpine324

ENV TITLE=OneOS \
    PIXELFLUX_WAYLAND=false \
    HARDEN_DESKTOP=true \
    NO_DECOR=true \
    NO_GAMEPAD=true \
    NO_WEBCAM=true \
    NO_STEAM=true

RUN apk add --no-cache \
      libreoffice-calc \
      libreoffice-draw \
      libreoffice-impress \
      libreoffice-writer \
      libreoffice-lang-ar \
      libreoffice-lang-de \
      libreoffice-lang-en_gb \
      font-carlito \
      font-dejavu \
      font-liberation \
      font-noto-arabic \
      inotify-tools \
      python3 \
      xdotool \
      xprintidle && \
    rm -rf /tmp/*

COPY --chmod=644 autostart /defaults/autostart
COPY --chmod=644 registrymodifications.xcu /defaults/one/registrymodifications.xcu
COPY --chmod=755 one-session /usr/local/bin/one-session

EXPOSE 3000 3100
