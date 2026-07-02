import argparse
import contextlib
import http.server
import os
import sys

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Inject headers to ensure the browser never caches or sends 304s
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

def main():
    # This parser mirrors the exact flags available in Python's standard http.server
    parser = argparse.ArgumentParser(prog="dev_server")
    parser.add_argument(
        '--bind', '-b', metavar='ADDRESS', default='all-interfaces',
        help='bind to this address (default: all interfaces, or localhost if specified)'
    )
    parser.add_argument(
        '--directory', '-d', default=os.getcwd(),
        help='serve this directory (default: current directory)'
    )
    parser.add_argument(
        'port', action='store', default=8000, type=int, nargs='?',
        help='bind to this port (default: %(default)s)'
    )
    
    args = parser.parse_args()

    # Align with http.server's handling of the default bind addresses
    bind_address = None if args.bind == 'all-interfaces' else args.bind

    # Changes directory seamlessly if --directory is passed 
    handler_class = NoCacheHandler
    if sys.version_info >= (3, 7):
        # Store the target directory in a local variable to read inside the class closure
        target_dir = args.directory
        
        class BoundDirectoryHandler(NoCacheHandler):
            def __init__(self, *handler_args, **handler_kwargs):
                # Pass directory down explicitly via keyword arguments
                handler_kwargs['directory'] = target_dir
                super().__init__(*handler_args, **handler_kwargs)
        
        handler_class = BoundDirectoryHandler

    # Run the server utilizing the standard http.server test routine
    with contextlib.suppress(KeyboardInterrupt):
        http.server.test(
            HandlerClass=handler_class,
            port=args.port,
            bind=bind_address
        )

if __name__ == '__main__':
    main()
