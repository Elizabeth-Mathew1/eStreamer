import React from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { Box, Button, Flex, Text } from '@chakra-ui/react'
import { IoTimeOutline } from 'react-icons/io5'
import { setTimeRange } from '../features/stream/streamSlice'

const TIME_RANGES = [
  { label: 'Last 5 minutes', seconds: 300 },
  { label: 'Last 10 minutes', seconds: 600 },
  { label: 'Last 30 minutes', seconds: 1800 },
  { label: 'Last 60 minutes', seconds: 3600 },
  { label: 'Last 2 hours', seconds: 7200 },
  { label: 'All time', seconds: null },
]

const TimeRangeSelector = () => {
  const dispatch = useDispatch()
  const selectedTimeRange = useSelector((state) => state.stream.timeRange)

  return (
    <Box mt={8}>
      <Flex align="center" gap={2} mb={4} color="blue.300">
        <IoTimeOutline size={26} />
        <Text color="white" fontSize="16px" fontWeight="semibold">
          Time Range
        </Text>
      </Flex>

      <Flex gap={4} wrap="wrap">
        {TIME_RANGES.map(({ label, seconds }, index) => (
          <Button
            key={seconds}   
            onClick={() => dispatch(setTimeRange(seconds))}
            background={
              selectedTimeRange === seconds
                ? 'linear-gradient(to right, rgb(42, 20, 183), #9f7aea)'
                : 'transparent'
            }
            color="white"
            border={selectedTimeRange === seconds ? 'none' : '2px solid'}
            borderColor={selectedTimeRange === seconds ? 'transparent' : 'gray.600'}
            borderRadius="lg"
            px={6}
            py={2}
            height="48px"
            fontSize="14px"
            fontWeight="medium"
            _hover={{
              borderColor: selectedTimeRange === seconds ? 'transparent' : 'gray.500',
            }}
          >
            {label}
          </Button>
        ))}
      </Flex>
      
    </Box>
  )
}

export default TimeRangeSelector

