import React from "react";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      errorInfo: null,
      error: null,
      maybeOldAnalysis: props.maybeOldAnalysis,
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI.
    console.log(error);
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // You can also log the error to an error reporting service
    // logErrorToMyService(error, errorInfo);
    console.log(error, errorInfo);
    this.setState({ hasError: true, errorInfo, error });
  }

  render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      return (
        <div className="error-boundary-ctr">
          {this.props.maybeOldAnalysis ? (
            <p className="text-red">
              You might need to re run this analysis for the latest version of
              the UI.
            </p>
          ) : (
            <p>Something went wrong.</p>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
