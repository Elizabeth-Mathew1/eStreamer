# YouTube Stream Analytics Frontend

Frontend application for real-time YouTube chat analytics built with React, Vite, Redux Toolkit, and Tailwind CSS.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```

3. Update `.env` with your API URL:
```
VITE_API_URL=https://your-cloud-run-url.run.app
```

## Development

Run the development server:
```bash
npm run dev
```

## Build

Build for production:
```bash
npm run build
```

## Deployment to Google Cloud Storage

1. Set environment variables:
```bash
export GCS_BUCKET_NAME=your-bucket-name
export GCP_PROJECT_ID=your-project-id
```

2. Run the deployment script:
```bash
./deploy_frontend.sh
```

The script will:
- Install dependencies
- Build the production bundle
- Upload to GCS bucket
- Configure static website hosting
- Set public read permissions

## Project Structure

```
youtube-stream-frontend/
├── public/
│   └── index.html
├── src/
│   ├── app/
│   │   └── store.js
│   ├── features/
│   │   ├── api/
│   │   └── stream/
│   ├── components/
│   │   ├── layout/
│   │   ├── controls/
│   │   ├── dashboard/
│   │   └── common/
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── .env
├── deploy_frontend.sh
├── package.json
├── tailwind.config.js
└── vite.config.js
```


