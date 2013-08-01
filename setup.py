from distutils.core import setup

setup(
    name='djaodjin-deployutils',
    version='0.1',
    author='The DjaoDjin Team',
    author_email='support@djaodjin.com',
    packages=['deployutils'],
    url='https://github.com/djaodjin/djaodjin-deployutils/',
    license='BSD',
    description='Management commands to deploy Django webapps',
    long_description=open('README.md').read(),
)
