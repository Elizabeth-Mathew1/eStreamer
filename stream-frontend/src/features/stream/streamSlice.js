import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  videoUrl: '',
  timeRange: null, 
  isAnalyzing: false,
}

const streamSlice = createSlice({
  name: 'stream',
  initialState,
  reducers: {
    setVideoUrl: (state, action) => {
      state.videoUrl = action.payload
    },
    setTimeRange: (state, action) => {
      state.timeRange = action.payload
    },
    setIsAnalyzing: (state, action) => {
      state.isAnalyzing = action.payload
    },
  },
})

export const { setVideoUrl, setTimeRange, setIsAnalyzing } = streamSlice.actions
export default streamSlice.reducer


