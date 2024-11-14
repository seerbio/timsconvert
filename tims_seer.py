from timsconvert import *
import os
import logging
from multiprocessing import Pool, cpu_count

def main():
    # Parse arguments.
    args = get_args()
    
    # Args check.
    args_check(args)
    
    # Check arguments.
    args['version'] = VERSION

    # Load in input data.
    input_files = []
    for dirpath in args['input']:
        if not dirpath.endswith('.d'):
            input_files += list(filter(None, dot_d_detection(dirpath)))
        elif dirpath.endswith('.d'):
            if os.path.isdir(dirpath):
                input_files.append(dirpath)
            else:
                logging.info(get_iso8601_timestamp() + ':' + f'{dirpath} does not exist...')
                logging.info(get_iso8601_timestamp() + ':' + 'Skipping...')

    # Convert each sample using multiprocessing with map.
    with Pool(processes=cpu_count() - 1) as pool:
        pool_map_input = []
        for infile in input_files:
            # Create a separate args dictionary for each file, setting 'input' as a single path
            run_args = args.copy()
            run_args['input'] = infile  # Set 'input' to a single directory path
            pool_map_input.append((run_args, infile))
        
        list_of_logfiles = pool.map(convert_raw_file, pool_map_input)
        
    # Filter out None results
    list_of_logfiles = list(filter(None, list_of_logfiles))

    # Shutdown logger.
    logging.shutdown()

    # Clean up temporary log files.
    clean_up_logfiles(args, list_of_logfiles)

if __name__ == '__main__':
    # Run the main function.
    main()
