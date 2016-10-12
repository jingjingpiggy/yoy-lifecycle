import sys, os, getopt
import paramiko

def printUsage():
    script_name = os.path.split(sys.argv[0])[-1]
    print("Usage:")
    print('python', script_name, '--priv_key <path + file name to save private key>',\
        '--pub_key <path + file name to save pub key>')
    print(os.linesep+"This script is to generate RSA SSH key pair and save in given location.")
        
def main():
    opts, args = getopt.getopt(sys.argv[1:], None,['priv_key=','pub_key='])
    priv_fn, pub_fn = None, None
    for opt, v in opts:
        if (opt == '--priv_key'):
            print(opt, v)
            priv_fn = v
        if (opt == '--pub_key'):
            print(opt, v)
            pub_fn = v
    
    if not priv_fn or not pub_fn:
        printUsage()
        print('\nUse default key file name: rsa_key.priv, rsa_key.pub')
        
    priv_fn = 'rsa_key.priv'
    pub_fn = 'rsa_key.pub'
    
    try:
        priv_file = open(priv_fn, 'w')
    except IOError:
        raise IOError('Fail to open private key file', priv_fn)
    try:
        pub_file = open(pub_fn, 'w')
    except IOError:
        priv_file.close()
        raise IOError('Fail to open public key file', pub_fn)
        
    key = paramiko.rsakey.RSAKey.generate(2048)
    
    try:
        key.write_private_key(priv_file)
    except:
        print('Failed to write private key to file', priv_fn)
        pub_file.close()
        raise
    finally:
        priv_file.close()
    
    pub_str = key.get_name()+' '
    pub_str += key.get_base64()
    user = ''
    while not user:
        user = input("Please input your email to login gerrit: ")
    pub_str += ' '
    pub_str += user
    try:
        pub_file.write(pub_str)
    except:
        print('Failed to write public key to file', pub_fn)
        print('Public key:', pub_str)
        raise
    finally:
        priv_file.close()
    
    print('\nDone. Key generated. Public key saved in', pub_fn, ', please copy its content to Gerrit.')
    print(pub_str, '\n')

if __name__ == '__main__':
    main()
