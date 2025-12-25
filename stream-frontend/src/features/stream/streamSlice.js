import { createSlice } from '@reduxjs/toolkit'
import { LOADING_STATUS } from '../../common'

const initialState = {
  videoUrl: '',
  duration: 864000, //TODO
  isAnalyzing: LOADING_STATUS.IDLE,
  analyticsData: null,
}

const streamSlice = createSlice({
  name: 'stream',
  initialState,
  reducers: {
    setVideoUrl: (state, action) => {
      state.videoUrl = action.payload
    },
    setDuration: (state, action) => {
      state.duration = action.payload
    },
    setIsAnalyzing: (state, action) => {
      state.isAnalyzing = action.payload
    },
    setAnalyticsData: (state, action) => {
      state.analyticsData = action.payload
    },

  },
})

export const { setVideoUrl, setDuration, setIsAnalyzing, setAnalyticsData } = streamSlice.actions
export default streamSlice.reducer


