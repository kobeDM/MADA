#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#include <signal.h>
#include <time.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <getopt.h>
#include "RBCP.h"
#include "SiTCP.h"

using namespace std;

int main(int argc, char* argv[]){

    bool debug =0;
    bool  end_flag = 0;
    int numperfile=1000;//default numofevents per file
    string filename;
    string IP;
    ofstream OutData;
    struct option longopts[] = {
        { "help", no_argument, NULL, 'h' },
        { "numperdir", required_argument, NULL, 'n' },
        { "filename", required_argument, NULL, 'f' },
        { "IP", required_argument, NULL, 'i' },
        { 0,        0,                 0,     0  },
    };

    int opt,longindex;
    int hopt=0;
    int numopt=0;
    while ((opt = getopt_long(argc, argv, "hn:f:i:", longopts, &longindex)) != -1) {
        switch (opt) {
        case 'h':
            hopt = 1;
            numopt++;
            break;

        case 'n':
            numopt+=2;
            numperfile=(atoi)(optarg);
            break;
        case 'i':
            numopt+=2;
            IP=optarg;
            break;
        case 'f':
            numopt+=2;
            filename=optarg;
            break;
        }
    }
    if(hopt){
        printf("MADA [-h || -help] [-n numperfile] [-f filename [-i IP");
        return 0;
    } 
    SiTCP EtherDAQ(IP);
    OutData.open(filename, ios::out);
    cout<<"Datafile "<<filename<<""<<std::endl;
    cout<<"IP:"<<IP<<endl;;
    
    char c_data[4096];
    int num = 0;
    int max_trig = numperfile;
    int trig_count = 0;

    std::cout << " refreshing buffer..." << std::flush;
    while( true ) {
        int num = EtherData.Read( c_data );
        if( num == 0 ) break; // assuming that software veto will successfully be running
    }
    std::cout << " done" << '\n' << std::flush;

    while(!end_flag){
        num = EtherDAQ.Read(c_data);
        if( num > 0 )
            OutData.write( c_data, num );

        if( num > 4096 ) { // will not enter this nest in principle
            cout << "warning: data overflow..." << endl;
            continue;
        }

        for( int i=0; i < num-3; ++i )
            if( c_data[i]   == 'u' && c_data[i+1] == 'P' && c_data[i+2] == 'I' && c_data[i+3] == 'C')
                trig_count += 1;

        cout << setw(6) << trig_count << "/" << setw(6) << max_trig << " counts stored\r";
        if( trig_count >= max_trig )  {
            OutData.close();
            end_flag=1;
        }
    }

    return 0;
}
