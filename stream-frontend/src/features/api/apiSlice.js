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
    
    /**
     * @returns {Promise<{
     *   avg_sentiment: number,
     *   top_topics: string[],
     *   top_chats: string[],
     *   top_users: Array<{user: string, no_of_messages: number}>
     * }>}
     */
    getAnalytics: builder.query({
      query: ({ video_id, duration }) => ({
        url: '/analyze',
        method: 'POST',
        body: { video_id, duration },
      }),
      transformResponse: (response) => {
        // Validate and ensure correct shape
        return {
          avg_sentiment: response.avg_sentiment ?? 0,
          top_topics: Array.isArray(response.top_topics) ? response.top_topics : [],
          top_chats: Array.isArray(response.top_chats) ? response.top_chats : [],
          top_users: Array.isArray(response.top_users) ? response.top_users : [],
        }
      },
    }),
 getKeyMoments: builder.mutation({
      query: (videoId) => ({
        url: '/download',
        method: 'POST',
        body: { video_id: videoId },
      }),
    }),

    // Poll endpoint - checks job status
    pollKeyMomentsStatus: builder.mutation({
      query: (videoUrl) => ({
        url: 'video/poll',
        method: 'GET',
        params: { live_video_url: videoUrl }
      }),
    }),

  }),
})


export const { 
  useStartStreamMutation, 
  useGetAnalyticsQuery,
  useLazyGetAnalyticsQuery,
  useGetKeyMomentsMutation,
  usePollKeyMomentsStatusMutation
  
} = apiSlice

