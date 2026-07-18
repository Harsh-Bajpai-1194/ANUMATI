import React from 'react';
// 1. Import your PDF component from the pages directory
import PdfUploadComponent from './pages/PdfUploadComponent';

const App = () => {
  return (
    <div>
      {/* 2. Render the component to the screen */}
      <PdfUploadComponent />
    </div>
  );
};

export default App;