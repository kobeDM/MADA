#define _USE_MATH_DEFINES
#include <iostream>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <thread>
#include <regex>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <getopt.h>
#include <sys/time.h>
#include <math.h>
#include <libm2k/m2k.hpp>
#include <libm2k/contextbuilder.hpp>
#include <libm2k/analog/m2kpowersupply.hpp>
#include <libm2k/analog/m2kanalogin.hpp>
#include <libm2k/analog/m2kanalogout.hpp>
#include <libm2k/digital/m2kdigital.hpp> //for dio
#include "rapidjson/document.h"
#include "rapidjson/error/en.h"
#include "rapidjson/istreamwrapper.h"
#include "RBCP.h"
#include "SiTCP.h"

#include "MADA_ad.hpp"
#include "MADA_iwaki.hpp"

using namespace std;
using namespace libm2k;
using namespace libm2k::analog;
using namespace libm2k::digital; //for dio
using namespace libm2k::context;

// uncomment the following definition to test triggering
#define TRIGGERING

int main(int argc, char* argv[]){
  printf("MADA: Miraclue Argon DAQ\n");

  int numperfile=1000;//default numofevents per file
  int numperdir=10;//default num of files per directory
  int maxnumADALM=8;
  int f_index=0;
  int fopt=0;
  //should be read from config file
  double dfreq[maxnumADALM];
  vector<string> MADALM_URI;
  vector<string> MADALM_SN;
  vector<string> gigaIwaki_NAME;
  vector<string> gigaIwaki_IP;
  vector<string> gigaIwaki_DAC;
  vector<int> gigaIwaki_Vth;
  vector<int> gigaIwaki_Active;
  //should be read from config file end

  char str_dummy[2];
  int numgigaIwaki;
  string filename_head;
  //option handling
  struct option longopts[] = {
      { "help", no_argument, NULL, 'h' },
      { "Mbytesperfile", required_argument, NULL, 'n' },
      { "numperdir", required_argument, NULL, 'n' },
      { "filename_head", required_argument, NULL, 'f' },
      { "verbose", no_argument, NULL, 'v' },
      { "slow_control_only", no_argument, NULL, 's' },
      { 0,        0,                 0,     0  },
  };
  int index;
  int opt;
  int longindex;
  int numopt=0;
  int hopt = 0;
  int nopt=0;
  int vopt=0;
  int sopt=0;
  int gopt=1;
  char filename[128];
  //  int BoardNo;
  
  while ((opt = getopt_long(argc, argv, "shvn:m:f:", longopts, &longindex)) != -1) {
    //    printf("%d %s\n", longindex, longopts[longindex].name);
    switch (opt) {
    case 'h':
      hopt = 1;
      numopt++;
      break;
    case 'v':
      vopt = 1;
      numopt++;
      break;
    case 's':
      sopt = 1;
      numopt++;
      break;
    case 'n':
      nopt = 1;
      numopt+=2;
      numperfile=(atoi)(optarg)<<20;
      break;
    case 'm':
      numopt+=2;
      numperdir=(atoi)(optarg);
      break;
    case 'f':
      nopt = 1;
      numopt+=2;
      filename_head=optarg;
      break;
    default:
      //      printf("error! \'%c\' \'%c\'\n", opt, optopt);
      return 1;
    }
  }
  
  if(hopt){
    //    cout<<"help message";
    printf("MADA [-h || -help] [-n numperfile] [-m numperdir] [-c (control only]\n");
    return 0;
  } 
  if(nopt){
  }
  //option handling end
  
  
  cout << "----Loading config file ----" << std::endl;
  ifstream ifs("MADA_config.json");
  rapidjson::IStreamWrapper isw(ifs);
  rapidjson::Document doc;
  doc.ParseStream(isw);
   if(doc.HasParseError()) {
    std::cout << "error offset:" << doc.GetErrorOffset() << std::endl;
    std::cout << "error parse:" << rapidjson::GetParseError_En(doc.GetParseError()) << std::endl;
   }

   //read general configurations
   const rapidjson::Value& ol =doc["general"];
   if(!doc["general"].IsObject()) {
     std::cout << "general is not a json Object. Check the config file." << std::endl;
     return 1;
   }
   cout <<"==general configs=="<<endl;   
   for(rapidjson::Value::ConstMemberIterator itrgl = ol.MemberBegin();
       itrgl != ol.MemberEnd(); itrgl++){
   }
   //read general configurations ends
   if(!sopt&&gopt){
   //read gigaIwaki configurations
   int gigaIwakiid=0;
   const rapidjson::Value& og =doc["gigaIwaki"];
   if(!doc["gigaIwaki"].IsObject()) {
     std::cout << "gigaiwaki is not a json Object. Check the config file." << std::endl;     
     return 1;
   }
   cout <<"==gigaIwaki configs=="<<endl;
   
   for(rapidjson::Value::ConstMemberIterator itrg = og.MemberBegin();
       itrg != og.MemberEnd(); itrg++){
     const char* name = itrg->name.GetString();
     cout<<name<<": ";
     gigaIwaki_NAME.insert(gigaIwaki_NAME.begin()+gigaIwakiid,name);
     const rapidjson::Value& oog = itrg->value;  
     gigaIwaki_Active.insert(gigaIwaki_Active.begin()+gigaIwakiid,oog["active"].GetInt());
     gigaIwaki_IP.insert(gigaIwaki_IP.begin()+gigaIwakiid,oog["IP"].GetString());
     gigaIwaki_DAC.insert(gigaIwaki_DAC.begin()+gigaIwakiid,oog["DACfile"].GetString());
     gigaIwaki_Vth.insert(gigaIwaki_Vth.begin()+gigaIwakiid,oog["Vth"].GetInt());   
     cout << "ACtive: " << gigaIwaki_Active[gigaIwakiid];
     cout << "IP: " << gigaIwaki_IP[gigaIwakiid];
     cout<<" Vth: "<< gigaIwaki_Vth[gigaIwakiid]<<endl;
     cout << "\tDACfile: " << gigaIwaki_DAC[gigaIwakiid] << std::endl;
     gigaIwakiid++;
   }
   numgigaIwaki=gigaIwakiid;   
   //read gigaIwaki configurations ends
   }
  
   //read adalm configurations
   int ADALMid=0;
   const rapidjson::Value& o =doc["ADALM"];
   if(!doc["ADALM"].IsObject()) {
     std::cout << "ADALM is not a json Object. Check the config file." << std::endl;
     return 1;
   }

   cout <<"==ADALM configs=="<<endl;
   for(rapidjson::Value::ConstMemberIterator itr = o.MemberBegin();
       itr != o.MemberEnd(); itr++){     
     const char* name = itr->name.GetString();
     cout<<name<<": ";
     const rapidjson::Value& oo = itr->value;     
     MADALM_URI.insert(MADALM_URI.begin()+ADALMid,oo["URI"].GetString());
     MADALM_SN.insert(MADALM_SN.begin()+ADALMid,oo["S/N"].GetString());
     dfreq[ADALMid] = oo["Clock_d"].GetDouble();
     cout << "URI: " << MADALM_URI[ADALMid];
     cout << " S/N: " << MADALM_SN[ADALMid] << std::endl;
     cout<<"\tClock(D): "<<scientific<<setprecision(1)<<  dfreq[ADALMid]<<" Hz"<<dec<<endl;
     ADALMid++;
   }
   int numADALM=ADALMid;

  cout << "----Loading config file, done. ----" << std::endl;

 //read adalm configurations ends
  M2k *MADALM[numADALM];
  M2kDigital *dMADALM[numADALM];
  
  //initial message
  if(sopt)cout<<"\trun-control only"<<endl;
  else{
    cout<<"with data aquisition."<<endl;
    //    printf("%d events per file will be recorded.\n",numperfile);
    cout<<"\t"<<scientific << setprecision(2) <<double(numperfile)<<" bytes will be recorded."<<endl;
    //    cout <<  events per file will be recorded.\n",
  }
  
  cout << "----Initializing ADALM boards ----" << std::endl;
  //ADALMs initilization
  for(int i=0;i<numADALM;i++){
    cout<<"\tInitializing MNADALM_"<<i;
    MADALM[i]=m2kOpen(MADALM_URI[i].c_str());
    if(vopt)    ad_showIDs(MADALM[i]);
    dMADALM[i] = MADALM[i]->getDigital(); //for digial io
    ad_d_setClock(dMADALM[i],dfreq[i]);
    ad_d_init(dMADALM[i]);
    cout<<", ok"<<endl;
  }
  ad_d_cyclic(dMADALM[1],false);
  cout << "----Initializing ADALM boards, done ----" << std::endl;
  if(sopt)numperdir=1;

  for(f_index=0;f_index<numperdir;f_index++){

//data taking
  ad_d_pulse(dMADALM[1],15);
  ad_d_latch_up(dMADALM[0]);
  cout<<"data size per file:"<<numperfile<<" bytes."<<endl;



  if(!sopt&&gopt){
  thread ths[numgigaIwaki];
  thread th0,th2;
  int BoardIDi;
  string BoardID;
  string filename_head_IP;
  ostringstream oss;
    
  for(int gigaIwakiid=0; gigaIwakiid<numgigaIwaki; gigaIwakiid++){
    if(gigaIwaki_Active[gigaIwakiid]){
      cout<<"Board "<< gigaIwakiid<<" ("<<gigaIwaki_IP[gigaIwakiid]<<") is active."<<endl;
      BoardIDi = (atoi)(gigaIwaki_IP[gigaIwakiid].substr(gigaIwaki_IP[gigaIwakiid].rfind('.')+1,gigaIwaki_IP[gigaIwakiid].size()-gigaIwaki_IP[gigaIwakiid].rfind('.')).c_str());
      //      cout<<"Board id:"<<BoardIDi <<endl;
      oss.str("");
      oss<< std::setfill('0') << std::right << std::setw(3)<<BoardIDi<<"_"<<std::setw(4)<<f_index<<flush;
      BoardID=oss.str();
      //filename_head_IP=regex_replace(filename_head, regex("thisIP"),BoardID);
      filename_head_IP=regex_replace(filename_head, regex("GBKB_thisIP"),gigaIwaki_NAME[gigaIwakiid]);
      //MADA_iwaki(gigaIwaki_IP[gigaIwakiid],filename_head_IP,numperfile);
      ths[gigaIwakiid]=thread(MADA_iwaki,gigaIwaki_IP[gigaIwakiid],filename_head_IP,numperfile);
      //cout <<"watching thread ID for IP "<<gigaIwaki_IP[gigaIwakiid]<<" with the thread ID "<< ths[gigaIwakiid].get_id()<<endl;

    }
  }
  for(int gigaIwakiid=0; gigaIwakiid<    numgigaIwaki; gigaIwakiid++){
    if(gigaIwaki_Active[gigaIwakiid]){
      ths[gigaIwakiid].join();
    }
  }
  }
  if(sopt){
    printf("\n");
    printf("carriage return>");
    scanf("%1[^\n]",str_dummy);
  }
  ad_d_latch_down(dMADALM[0]);  
  }//end of f_index loop
  return 0;
}
