import { Box, Text, Flex } from '@chakra-ui/react'
import { useSelector } from 'react-redux'
import Loader from './Loader'
import SentimentBox from './SentimentBox'
import TopChats from './TopChats'
import MostActiveUsers from './MostActiveUsers'
import HotTopics from './HotTopics'
import { LOADING_STATUS } from '../common'
import PredictiveAnalysis from './PredictiveAnalysis'




function Analytics() {

    const isAnalyzing = useSelector((state) => state.stream.isAnalyzing)

    if (isAnalyzing === LOADING_STATUS.LOADING) {
        return <Loader />
    }
    else if (isAnalyzing === LOADING_STATUS.SUCCESS) {
        return (
            <Box>  
                <PredictiveAnalysis />
                <SentimentBox />
              
                <Flex pt={6} gap={6} align="stretch" height="500px">
                    <TopChats />
                    <MostActiveUsers />
                </Flex>
                <HotTopics />
            </Box>
        )
    }
}

export default Analytics