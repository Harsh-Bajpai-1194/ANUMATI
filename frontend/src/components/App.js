import React from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import Dashboard from './Dashboard';
import EvaluatorView from './EvaluatorView';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/evaluator" element={<EvaluatorView />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;