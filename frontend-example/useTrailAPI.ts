// hooks/useTrailAPI.ts
import { useState } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';
const API_KEY = 'trail-ai-secret-key-2024'; // Move to .env in production

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json',
  },
});

export const useTrailAPI = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = async (message: string, sessionId?: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.post('/chat', {
        message,
        session_id: sessionId,
      });
      
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'API error');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const getHealth = async () => {
    try {
      const response = await apiClient.get('/health');
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Health check failed');
      throw err;
    }
  };

  return {
    sendMessage,
    getHealth,
    loading,
    error,
  };
};