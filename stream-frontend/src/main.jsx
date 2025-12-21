import React from 'react'
import ReactDOM from 'react-dom/client'
import { Provider } from 'react-redux'
import { ChakraProvider, createSystem, defaultConfig } from '@chakra-ui/react'
import App from './App.jsx'
import { store } from './app/store.js'
import './index.css'

const system = createSystem(defaultConfig)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ChakraProvider value={system}>
    <Provider store={store}>
      <App />
    </Provider>
    </ChakraProvider>
  </React.StrictMode>,
)


