FROM registry.fedoraproject.org/fedora:44

ARG PYTHON_FLAVOR=standard

RUN dnf -y update \
    && if [ "$PYTHON_FLAVOR" = "freethreaded" ]; then \
        dnf -y install python3.14-freethreading python3.14-freethreading-devel python3-pip poppler-utils; \
    else \
        dnf -y install python3.14 python3.14-devel python3-pip poppler-utils; \
    fi \
    && dnf clean all

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src

RUN if [ "$PYTHON_FLAVOR" = "freethreaded" ]; then \
        python3.14t -m pip install --no-cache-dir --upgrade pip && python3.14t -m pip install --no-cache-dir -e .; \
    else \
        python3.14 -m pip install --no-cache-dir --upgrade pip && python3.14 -m pip install --no-cache-dir -e .; \
    fi

ENTRYPOINT ["planner"]
