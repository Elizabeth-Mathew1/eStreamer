import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'

// In development, use proxy (/api). In production, use full URL
const baseUrl = import.meta.env.DEV
  ? '/api' // Vite proxy will forward to Cloud Run
  : import.meta.env.VITE_API_URL || 'https://stream-server-437245115270.us-central1.run.app'

const baseQuery = fetchBaseQuery({
  baseUrl,
})

export const apiSlice = createApi({
  baseQuery,
  tagTypes: [],
  endpoints: (builder) => ({
    startStream: builder.mutation({
      query: (videoId) => ({
        url: '/video_id',
        method: 'POST',
        body: { video_id: videoId },
      }),
    }),
  }),
})

export const { useStartStreamMutation } = apiSlice

