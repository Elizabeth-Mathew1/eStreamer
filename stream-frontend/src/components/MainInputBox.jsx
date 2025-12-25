import React from 'react'
import { Box, Text, Flex } from '@chakra-ui/react'
import StreamURLInput from './StreamURLInput'
import TimeRangeSelector from './TimeRangeSelector'
import KeyMoments from './Download'
function MainInputBox() {
    return (
        <Box display="flex" flexDirection="column" gap={2} backgroundColor="gray.900" p={4} borderRadius="xl" py={8} px={10}>
           <StreamURLInput />
           <TimeRangeSelector />
           <KeyMoments />
        </Box>
    )
}

export default MainInputBox