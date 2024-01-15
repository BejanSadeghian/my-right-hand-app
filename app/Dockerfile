FROM python:3.12
WORKDIR /app
COPY . /app

# Install Poetry
RUN pip install poetry

# Use Poetry to install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Make port 8501 available to the world outside this container
EXPOSE 8501
CMD ["streamlit", "run", "Home.py"]