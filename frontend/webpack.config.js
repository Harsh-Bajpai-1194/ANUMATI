const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  // Set the base directory for resolving entry points and loaders
  context: __dirname,
  // The entry point of your app
  entry: './src/index.js',
  
  // Where to put the bundled code
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'main.js',
    publicPath: '/',
  },
  
  // Rules for how to handle different file types
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/, // Handle both .js and .jsx files
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader'
        }
      }
    ]
  },
  
  // Automatically resolve these extensions
  resolve: {
    extensions: ['.js', '.jsx']
  },
  
  // Generates the index.html file
  plugins: [
    new HtmlWebpackPlugin({
      template: './public/index.html'
    })
  ],
  
  // Configuration for the development server
  devServer: {
    static: {
      directory: path.join(__dirname, 'public'),
    },
    port: 8080,
    // This is crucial for react-router to work correctly
    historyApiFallback: true,
  },
};